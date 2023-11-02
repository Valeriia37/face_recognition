import pickle
import datetime
import logging
import os
from db import db


logging.basicConfig(filename='LogFile',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)


class DataBaseRequests:

    def __init__(self):
        self.user_table = db('vface_user')
        self.log_table = db('vface_log')
        self.mer_table = db('vface_api_merchant')


    def client_validation(self, clientname: str, key: str):
        '''
            Validate client info
            When verification passes, return merid
        '''
        logging.info(f'Validation of {clientname} ...')
        merid_dict = self.mer_table.field('id').where(f'f_username = {clientname} and f_key = {key}').limit(1).find()

        if len(merid_dict) == 1:
            logging.info('Validation successed')
            return merid_dict[0]['id']
        else:
            logging.error('Validation failed')



    def insert_log(self, merid: str, api: str, status: int, requestdata, responsedata):
        try:
            self.log_table.add({'f_merid': merid, 'f_api': api, 'f_status': status, 'f_requestdata': requestdata,
                            'f_responsedata': responsedata, 'f_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        except Exception as e:
            logging.error(f'Insert log {str(e)}')


    def get_users_info(self, group_id: str, merid: str):
        face_encodings = []
        face_ids = []
        face_info = []

        rows = self.user_table.where(f'f_groupid = {group_id} and f_merid = {merid}').find()
        if rows:
            for row in rows:
                if row['f_encode']:
                    face_encode = pickle.loads(row['f_encode'])
                    face_encodings.append(face_encode)
                    face_info.append(row['f_userinfo'])
                    face_ids.append(row['f_uid'])
                    
            print(f'{len(face_encodings)} faces in group #{group_id}')
            print(f'Ids: {face_ids}')
            logging.info(f'{len(face_encodings)} faces in group #{group_id}')
            return face_ids, face_info, face_encodings
        return False
    

    def update_user(self, merid: str, groupid: str, uid: str, encode, userinfo: str) -> str:
        '''
            return status
                - 'Updated'
                - 'Created'
                - 'Failed'
        '''
        if type(encode) != bytes:
            encode = pickle.dumps(encode)
        
        print('Updating...')
        try:
            rows = self.user_table.where(f'f_merid = {merid} and f_groupid = {groupid} and f_uid = {uid}').limit(1).find()
            if len(rows) == 1:
                logging.info(f'Updating {uid}...')
                self.user_table.where(f'f_merid = {merid} and f_groupid = {groupid} and f_uid = {uid}').save({'f_encode': encode, 'f_userinfo': userinfo,
                                                                                                              'f_etime': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                logging.info(f'{uid} user was updated')
                status = 'Updated'
            elif len(rows) == 0:
                logging.info(f'Creating {uid}...')
                self.user_table.add({'f_merid': merid, 'f_groupid': groupid, 'f_uid': uid, 'f_encode': encode, 'f_userinfo': userinfo, 
                                     'f_ctime': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                     'f_etime': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                logging.info(f'{uid} user was created.')
                status = 'Created'
                
        except Exception:
            logging.error(f'Database request failed')
            status = 'Failed'
        return status


if __name__ == '__main__':
    from face_recognition_code import FaceRecognition
    fr = FaceRecognition()
    database = DataBaseRequests()
    face_encoding = fr.encoding_face_img(face_img=(os.path.join(r'.\faces', 'elon.jpg')), img_type='PATH')
    database.update_user(1,'1','153', face_encoding, 'Information detail')
    database.get_users_info('1', '1')
    print()