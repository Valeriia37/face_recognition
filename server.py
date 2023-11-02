from http.server import HTTPServer, BaseHTTPRequestHandler
from http import HTTPStatus
import json
from db_requests import DataBaseRequests
from face_recognition_code import FaceRecognition
import logging
import configparser
import datetime

config = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')


logging.basicConfig(filename='LogFile',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)



class HTTPRecognitionServer(BaseHTTPRequestHandler):

    fr = FaceRecognition()
    data_cache = {}
    access_cache = {}
    # access_cache = {'admin': {'key': 123, 'merid': 1,'ex_time': now()}}
    # Lifetime of storing passwords in cache for fast connection
    pwd_time_delta = datetime.timedelta(days=1)
    # Lifetime of storing fase info in cache for fast connection
    time_delta = datetime.timedelta(hours=2)
    bd_config = config['MYSQL']
    db = DataBaseRequests(host=bd_config['host'], user=bd_config['user'], pwd=bd_config['pwd'], database=bd_config['database'])



    def _set_headers(self):
        self.send_response(HTTPStatus.OK.value)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()


    def send_msg(self, status_code, msg, data=None):
        self._set_headers()
        result = {'status_code': status_code, 'msg': msg}
        if data:
            result['data'] = data
        self.wfile.write(json.dumps(result).encode('utf-8'))


    def do_GET(self):
        """
            Get get request function.
        """
        self._set_headers()
        self.wfile.write(b'Hello!')


    def do_POST(self):
        """
            Get post request function.
        """
        print('-----START------')
        print(f'Get post request time = {datetime.datetime.now()}')
        try:
            if self.path == '/update':
                print('I get update data request!')
                self.check_request_body()
                
                merid = self.client_validation(self.body)
                status = self.update_post(merid, self.body['data'])

                if status == 'Failed':
                    raise Exception('Database request failed.')
                else:
                    self.db.insert_log(merid, self.path, 1, json.dumps(self.body), status)
                    self.send_msg(200, status)

            elif self.path == '/recognition':
                print('I get data request for recognition!')
                self.check_request_body()
                print(f'Check time = {datetime.datetime.now()}')
                merid = self.client_validation(self.body)
                print(f'Validation time = {datetime.datetime.now()}')
                result = self.recognition_post(merid, self.body['data'])
                print(f'Recognition finished time = {datetime.datetime.now()}')
                logging.info(json.dumps(result))
                self.send_msg(200, 'Ok', result)
                print(f'Send time = {datetime.datetime.now()}')
                self.db.insert_log(merid, self.path, 1, json.dumps(self.body), json.dumps(result))

            elif self.path == '/clear':
                print('I get request to clean cache data!')
                self.check_request_body()
                merid = self.client_validation(self.body)
                msg = self.clear_cache_post(merid, self.body['data'])
                self.send_msg(200, 'Ok', msg)
                self.db.insert_log(merid, self.path, 1, json.dumps(self.body), json.dumps(msg))

            else:
                self.send_error(404, 'The request path structure is incorrect.')
            print(f'End time = {datetime.datetime.now()}')
            

        except Exception as e:
            if 'merid' not in locals():
                merid = 0
            self.db.insert_log(merid, self.path, 2, json.dumps(self.body), str(e))
            self.send_msg(400, str(e))



    def clear_cache_post(self, merid, data):
        gid = data.get('gid')
        dataKey = f'{merid}_{gid}'
        if gid and dataKey in self.data_cache.keys():
            del self.data_cache[dataKey]
            return f'Successfully cleared cache associated with group {gid}.'
        else:
            raise Exception('The request data structure is incorrect or the data cache does not have relevant data.')


    def check_request_body(self):
        accept = self.headers.get('Accept')
        content_len = int(self.headers['Content-Length'])
        self.body = self.rfile.read(content_len)
        if 'application/json' or '*/*' in accept:
            try:
                self.body = json.loads(self.body)
            except:
                raise Exception('Only accept json request format.')
        else:    
            raise Exception('No correction request acceptance format.')
        


    def client_validation(self, body):
        api = body.get('api')
        data = body.get('data')

        if api and data:
            client = api.get('client')
            key = api.get('key')

            if client and key:

                self.check_cache(self.access_cache, self.pwd_time_delta)
                try:
                    
                    access_data = self.access_cache.get(client)
                    access_key = access_data.get('key')
                    access_merid = access_data.get('merid')
                    
                    if access_key == key:
                        return access_merid
                    else:
                        raise Exception('The key is wrong')

                except:
                    # validate client through database
                    merid = self.db.client_validation(client, key)

                    if merid == -1:
                        raise Exception('Database connection failed.')
                    
                    elif not merid:
                        raise Exception('Invalid client id or key. Access denied.')
                    
                    else:
                        self.access_cache[client] = {'key': key, 'merid': merid,'ex_time': datetime.datetime.now()}
                        return merid
                
        raise Exception('The request data structure is incorrect. Access denied.')
    



    def update_post(self, merid, data): 
        """
            Update face images in database
        """
        if 'gid' and 'uid' and 'info' and 'img' in data.keys():

            encode = self.fr.encoding_face_img(face_img=data['img'])

            if encode is not None:
                return self.db.update_user(merid, data['gid'], data['uid'], encode, data['info'])
            
            else:
                raise Exception('Encoding failed. There are no faces on the image.')
            
        else:
            raise Exception('The request data structure is incorrect. Access denied.')


    def recognition_post(self, merid, data:dict):

        gid = data.get("gid")
        threshold = data.get('threshold')
        confidence = data.get('conf')
        image = data.get('img')
        dataKey = f'{merid}_{gid}'


        if gid and threshold and image:

            self.check_cache(self.data_cache, self.time_delta)
            recognition_cache = self.data_cache.get(dataKey)

            if recognition_cache:
                
                recognition_tdata = recognition_cache.get('data')
                face_ids, face_info, face_encodings = recognition_tdata
                print(f'Recognizer starttime = {datetime.datetime.now()}')
                flag, msg = self.fr.face_recognizer(encodings=face_encodings, user_ids=face_ids, user_infos=face_info, img=image, threshold=threshold)
                print(f'Recognizer finishtime = {datetime.datetime.now()}')

                if flag:
                    return {'info': {'gid': gid, 'merid': merid}, 'data': msg}
                else:
                    raise Exception(msg)

            else:
                t_data = self.db.get_users_info(group_id=gid, merid=merid)

                if t_data is not False:
                    face_ids, face_info, face_encodings = t_data
                    print(f'Recognizer starttime = {datetime.datetime.now()}')
                    flag, msg = self.fr.face_recognizer(encodings=face_encodings, user_ids=face_ids, user_infos=face_info, img=image, threshold=threshold)
                    print(f'Recognizer finishtime = {datetime.datetime.now()}')

                    self.data_cache[dataKey] = {
                        'data': t_data,
                        'ex_time': datetime.datetime.now(),
                        'lenght':len(t_data[0])
                    }

                    if flag:
                        return {'info': {'gid': gid, 'merid': merid}, 'data': msg}
                    else:
                        raise Exception(msg)
                else:
                    raise Exception('Unable to connect to the database when obtaining face information.')
                
        else:
            raise Exception('The request data structure is incorrect. Access denied.') 



    def check_cache(self, cache:dict, time_delta:datetime) -> None:
        """
            clean expaired cache data function
        """
        now = datetime.datetime.now()
        data = cache.copy()
        for key, info in data.items():
            if info['ex_time'] + time_delta < now:
                del cache[key]




def start_server(host, port):
    http_server = HTTPServer((host, int(port)), HTTPRecognitionServer)
    http_server.serve_forever()




if __name__ == '__main__':
    server_config = config['SERVER']
    start_server(server_config['host'], server_config['port'])