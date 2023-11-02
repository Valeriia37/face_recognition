import face_recognition
import os, io
import numpy as np
import pickle
import math
import base64
from PIL import Image
import logging


logging.basicConfig(filename='LogFile',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)


# Helper
def face_confidence(face_distance, face_match_threshold=0.6):
    range = (1.0 - face_match_threshold)
    linear_val = (1.0 - face_distance) / (range * 2.0)

    if face_distance > face_match_threshold:
        return round(linear_val * 100, 3)
    else:
        value = (linear_val + ((1.0 - linear_val) * math.pow((linear_val - 0.5) * 2, 0.2))) * 100
        return round(value, 3)


class FaceRecognition:
    FACE_PATH = r'.\faces'
    face_locations = []
    face_encodings = []
    face_names = []
    known_face_encodings = []
    known_face_names = []
    known_face_ids = []
    process_current_frame = True

    def __init__(self):
        self.__create_foldes()


    def __create_foldes(self):
        if not os.path.exists(self.FACE_PATH):
            os.makedirs(self.FACE_PATH)

    def transform_encoding_to_array(encodings : list) -> list:
        array_encodings = []
        for encoding in encodings:
            array_encodings.append(pickle.loads(encoding))
        return array_encodings


    def encoding_face_img(self, face_img, img_type='BASE64'):
        
        """
            The function accepts two types of images: BASE64 and PATH
        """
        if img_type == 'BASE64':
            img = base64.b64decode(face_img)
            img = Image.open(io.BytesIO(img))
            try:
                img_path = os.path.join(self.FACE_PATH, 'img.jpg')
                img.save(img_path)
            except:
                img_path = os.path.join(self.FACE_PATH, 'img.png')
                img.save(img_path)

        elif img_type == 'PATH':
            img_path = face_img

        else:
            # when the type is not BASE64 and PATH
            return False
        
        face_image = face_recognition.load_image_file(img_path)

        try:
            face_encoding = face_recognition.face_encodings(face_image)[0]
        except IndexError:
            print('Encoding is failed. No face on the image')
            logging.error('Encoding is failed. No face on the image.')
            face_encoding = None

        if img_type != 'PATH':
            os.remove(img_path)
        logging.info('Image encoded')
        return face_encoding
    


    def get_image(self, face_img, img_type='BASE64'):
        """
            The function accepts two types of images: BASE64 and PATH
        """
        if img_type == 'BASE64':
            img = base64.b64decode(face_img)
            img = Image.open(io.BytesIO(img))
            try:
                img_path = os.path.join(self.FACE_PATH, 'img.jpg')
                img.save(img_path)
            except:
                img_path = os.path.join(self.FACE_PATH, 'img.png')
                img.save(img_path)

        elif img_type == 'PATH':
            img_path = face_img

        else:
            # when the type is not BASE64 and PATH
            return False
        face_image = face_recognition.load_image_file(img_path)

        if img_type != 'PATH':
            os.remove(img_path)
        return face_image


    def face_recognizer(self, encodings:list, user_ids:list, user_infos:list, img, img_type='BASE64', threshold=0.9):
        '''
            return (flag, msg)
        '''
        face_image = self.get_image(img, img_type)

        face_locations = face_recognition.face_locations(face_image)
        face_encodings = face_recognition.face_encodings(face_image=face_image, known_face_locations=face_locations)
        recognition_res = []

        for face_encoding in face_encodings:
            data_confidence = {}

            # Calculate the shortest distance to face
            face_distances = face_recognition.face_distance(encodings, face_encoding)
            matches = face_recognition.compare_faces(encodings, face_encoding)
            best_match_index = np.argmin(face_distances)

            # for i in range(0, 5):
            #     data = {}
            #     best_match_index = np.argmin(face_distances)
            #     if matches[best_match_index]: 
            #         data['id'] = user_ids[best_match_index]
            #         data['conf'] = face_confidence(face_distances[best_match_index])
            #         data['info'] = user_infos[best_match_index]
            #         face_distances[best_match_index] = 1
            #         data_confidence.append(data)
            # recognition_res.append(data_confidence)
            
            confidenve = face_confidence(face_distances[best_match_index])

            if matches[best_match_index] and confidenve > (threshold*100):
                data_confidence['id'] = user_ids[best_match_index]
                data_confidence['conf'] = confidenve
                data_confidence['info'] = user_infos[best_match_index]
                recognition_res.append(data_confidence)

        if recognition_res:
            # print('------RESULT------')
            # print(f'Ok. {recognition_res}')
            # print('------END------')
            logging.info(f'Face recognition result = {recognition_res}')
            return True, recognition_res
        else:
            # print(f'Face recognition is failed. No matched faces.')
            logging.warning('Face recognition is failed. No matched faces.')
            return False, 'Face recognition is failed. No matched faces.'


if __name__ == '__main__':
    fr = FaceRecognition()
    print(fr.encoding_face_img(face_img='829619c2-09b0-11ee-a87c-2811a80d8c79.jpg', img_type='PATH'))
    
