from flask import Flask, request
from pymongo import MongoClient
import numpy as np
import time
import dlib
import cv2
import base64

app = Flask(__name__)

# MongoDB DB이름 : DB_animated_conference_server
client = MongoClient('localhost', 27017)
db = client.DB_animated_conference_server

# face detector와 landmark predictor 정의
# predict 파일 다운로드해 이 파일과 같은 위치에 저장 (http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2)
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# 서버 접속 테스트용 처음화면 http://animated-facial-expression-conference.shop:5000/
@app.route('/')
def hello():
    return f'This is sever of \"Face Expression Transfer Application\"' \
           'by Yonsei EE application-programming class team 3 '

# Android: 안드로이드에서 방 생성 (POST) API
@app.route('/open-new-room', methods=['POST'])
def open_new_room():
    # 안드로이드에서 방번호, 방비밀번호, user_key를 입력받아 서버로 전송
    room_num_receive = int(request.json['room_num'])
    room_password_receive = int(request.json['room_password'])
    user_key_receive = request.json['user_key']

    # 디버그
    print(f"{user_key_receive} Opened [ room num : {room_num_receive}, password : {room_password_receive} ]")

    # DB에 있는 데이터인지 확인
    if db.user_room_list.find_one({'room_num': room_num_receive}) != None:
        # DB에 이미 있는 방번호인 경우

        # 디버그
        print("open-new-room : Already existing room number")

        # 이미 있는 방번호라는 메세지 return
        return {"msg": 'Already existing room number'}
    # DB에 없을 경우
    else:
        # 서버에 저장할 내용
        user_room_list = {
            'room_num': room_num_receive,
            'room_password': room_password_receive,
            'user_key': user_key_receive,
            'time': time.strftime('%y-%m-%d %H:%M:%S')
        }
        # 서버에 저장
        db.user_room_list.insert_one(user_room_list)
        return {"msg": 'New room created'}

# Android : 안드로이드에서 방 참여 (POST) API
@app.route('/enter-room', methods=['POST'])
def enter_room():
    # 안드로이드에서 방번호, 방비밀번호, user_key를 입력받아 서버로 전송
    room_num_receive = int(request.json['room_num'])
    room_password_receive = int(request.json['room_password'])
    user_key_receive = request.json['user_key']

    # DB에 방이 있는지 확인
    if db.user_room_list.find_one({'room_num': room_num_receive}) != None:
        # 비밀번호가 맞는지 확인
        if db.user_room_list.find_one({'room_num': room_num_receive})['room_password'] == room_password_receive:
            # 비밀번호가 맞는 경우
            # 서버에 저장할 내용
            user_room_list = {
                'room_num': room_num_receive,
                'room_password': room_password_receive,
                'user_key': user_key_receive,
                'time': time.strftime('%y-%m-%d %H:%M:%S')
            }
            # 서버에 저장
            db.user_room_list.insert_one(user_room_list)

            # 디버그
            print(f"{user_key_receive} Entered [ room num : {room_num_receive}, password : {room_password_receive} ]")

            # DB에 정보 추가되었을때 방에 성공적으로 입장했다는 메세지 return
            return {"msg": 'Room enter success'}
        # 비밀번호가 다른 경우
        else:
            # 디버그
            print("enter-room : Wrong password")

            # 비밀번호가 다를 때 비밀번호가 다르다는 메세지 return
            return {"msg": 'Wrong Password'}
    # DB에 방이 없는 경우
    else:
        # 디버그
        print("enter-room : No room number")

        # 방이 없을때 입력한 방이 없다는 메세지 return
        return {"msg": 'No room number'}

# Android : 안드로이드에서 사진 전송받아 랜드마크로 변환 (POST) API
@app.route('/image-landmark', methods=['POST'])
def image_landmark():
    # 안드로이드에서 방번호, user_key, base64 형식의 이미지를 전송
    room_num_receive = int(request.json['room_num'])
    user_key_receive = request.json['user_key']
    image_receive = request.json['bmpimg']

    # 디버그
    print(f"from Android, image sent : {room_num_receive}, {user_key_receive}")

    # ---------- 랜드마크 따는 파트 ----------
    # face detector와 landmark predictor 정의
    global detector
    global predictor

    # base64 이미지 read
    try:
        decoded_data = base64.b64decode(image_receive)
        np_data = np.frombuffer(decoded_data, np.uint8)
        img = cv2.imdecode(np_data, cv2.IMREAD_UNCHANGED)
    except:
        # 디버그
        print('Image read failed')

        return {"msg": 'Image read failed'}

    # resize
    r = 600. / img.shape[1]
    dim = (600, int(img.shape[0] * r))
    resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

    # 얼굴 detection
    try:
        # 얼굴이 있는 사각형 detect
        rect = detector(resized, 1)[0]

        # 얼굴 랜드마크 68개 점 detect
        shape = predictor(resized, rect)

        # 점들을 리스트로 저장
        landmarks = []
        for j in range(68):
            x, y = shape.part(j).x, shape.part(j).y
            landmarks.append([x, y])
            # # 디버그 : facial landmark를 빨간색 점으로 찍어서 표현
            # cv2.circle(resized, (x, y), 1, (0, 0, 255), -1)
    # 얼굴 인식에 실패할 경우
    except:
        # 디버그 print
        print('Face read failed')
        return {"msg": 'Face read failed'}

    # # 디버그 사진확인
    # cv2.imshow('image', resized)
    # key = cv2.waitKey(0)

    # 유니티로 전송할 변수들 계산
    # 왼쪽 눈 변수
    eye_left = (((landmarks[43][0]-landmarks[47][0])**2+(landmarks[43][1]-landmarks[47][1])**2)**(1/2)+
                ((landmarks[44][0]-landmarks[46][0])**2+(landmarks[44][1]-landmarks[46][1])**2)**(1/2))\
               /2/(((landmarks[42][0]-landmarks[45][0])**2+(landmarks[42][1]-landmarks[45][1])**2)**(1/2))
    # 오른쪽 눈 변수
    eye_right = (((landmarks[38][0]-landmarks[40][0])**2+(landmarks[38][1]-landmarks[40][1])**2)**(1/2)+
                 ((landmarks[37][0]-landmarks[41][0])**2+(landmarks[37][1]-landmarks[41][1])**2)**(1/2))\
                /2/(((landmarks[36][0]-landmarks[39][0])**2+(landmarks[36][1]-landmarks[39][1])**2)**(1/2))
    # 입 벌어진 정도 변수
    mouth_openclose = (((landmarks[50][0]-landmarks[58][0])**2+(landmarks[50][1]-landmarks[58][1])**2)**(1/2)+
                        ((landmarks[51][0]-landmarks[57][0])**2+(landmarks[51][1]-landmarks[57][1])**2)**(1/2)+
                        ((landmarks[52][0]-landmarks[56][0])**2+(landmarks[52][1]-landmarks[56][1])**2)**(1/2))\
                       /3/(((landmarks[48][0]-landmarks[54][0])**2+(landmarks[48][1]-landmarks[54][1])**2)**(1/2))
    # 입 왼쪽 기울기 변수
    mouth_inclination_left = abs((landmarks[54][1]-(landmarks[62][1]+landmarks[66][1])/2)/(landmarks[54][0]-(landmarks[62][0]+landmarks[66][0])/2))
    # 입 오른쪽 기울기 변수
    mouth_inclination_right = abs((landmarks[48][1]-(landmarks[62][1]+landmarks[66][1])/2)/(landmarks[48][0]-(landmarks[62][0]+landmarks[66][0])/2))

    # ---------- 입력받은 변수로 db 업데이트 ----------
    # 유저_룸 DB에 입력받은 번호의 방과 유저 정보가 있을 때
    if db.user_room_list.find_one({'room_num': room_num_receive, 'user_key': user_key_receive}) != None:
        # 랜드마크 DB에 입력받은 번호의 방에 유저 키 있을 때 - 기존 정보 변경
        if db.landmarks_list.find_one({'room_num': room_num_receive, 'user_key': user_key_receive}) != None:
            # id로 찾아 서버 데이터 업데이트
            data_id = db.landmarks_list.find_one({'room_num': room_num_receive, 'user_key': user_key_receive})['_id']
            db.landmarks_list.update_one({'_id': data_id}, {'$set': {'eye_left': eye_left}})
            db.landmarks_list.update_one({'_id': data_id}, {'$set': {'eye_right': eye_right}})
            db.landmarks_list.update_one({'_id': data_id}, {'$set': {'mouth_openclose': mouth_openclose}})
            db.landmarks_list.update_one({'_id': data_id}, {'$set': {'mouth_inclination_left': mouth_inclination_left}})
            db.landmarks_list.update_one({'_id': data_id}, {'$set': {'mouth_inclination_right': mouth_inclination_right}})
            db.landmarks_list.update_one({'_id': data_id}, {'$set': {'time': time.strftime('%y-%m-%d %H:%M:%S')}})
            print('Landmark updated success')
            return {"msg": 'Landmark updated success'}

        # 입력받은 번호의 방에 유저 키 없을 때 - 정보 새로 추가
        else:
            # 서버에 저장할 내용
            room_landmark = {
                'room_num': room_num_receive,
                'user_key': user_key_receive,
                'eye_left': float(eye_left),
                'eye_right': float(eye_right),
                'mouth_openclose': float(mouth_openclose),
                'mouth_inclination_left': float(mouth_inclination_left),
                'mouth_inclination_right': float(mouth_inclination_right),
                'time': time.strftime('%y-%m-%d %H:%M:%S')
            }
            # 서버에 저장
            db.landmarks_list.insert_one(room_landmark)
            # 디버그
            print('from Android, Landmark inserted success')
            return {"msg": 'Landmark inserted success'}

    # DB에 입력받은 방번호와 유저 정보가 없을 때
    else:
        return {"msg": 'No room number or No user key'}

# Unity : 유니티로 랜드마크 전송 (GET) API
@app.route('/landmark-return', methods=['GET'])
def landmark_return():
    # Unity 에서 방 번호와, 0, 1, 2, 3 ... 의 숫자로 한명씩 랜드마크를 요청
    room_num_receive = int(request.args.get('room_num'))
    user_num_receive = int(request.args.get('user_num'))

    # 요청받은 인자로 방에 있는 유저들의 랜드마크 변수를 리스트에 담음
    room_member_list = list(db.landmarks_list.find({'room_num': int(room_num_receive)}))

    # 디버그
    print(f"from Unity, landmark requested: {room_num_receive}, {user_num_receive}")

    # 리스트[0], 리스트[1], [2], ... 의 원소들에서 값을 json 형식으로 return
    try:
        return {
            'user_key': room_member_list[user_num_receive]['user_key'],
            'eye_left': room_member_list[user_num_receive]['eye_left'],
            'eye_right': room_member_list[user_num_receive]['eye_right'],
            'mouth_openclose': room_member_list[user_num_receive]['mouth_openclose'],
            'mouth_inclination_left': room_member_list[user_num_receive]['mouth_inclination_left'],
            'mouth_inclination_right': room_member_list[user_num_receive]['mouth_inclination_right'],
            'Valid': "True"
        }
    # 리스트에 원소가 더 없을 경우, Valid: False 반환으로 유니티에 리스트의 끝을 알림
    except:
        return {
            'user_key': 0,
            'eye_left': 0,
            'eye_right': 0,
            'mouth_openclose': 0,
            'mouth_inclination_left': 0,
            'mouth_inclination_right': 0,
            'Valid': "False"
        }

# Unity : 유니티에서 변환된 애니메이션 이미지 받아 저장 (POST) API
@app.route('/animated-image', methods=['POST'])
def animated_image():
    # Unity 에서 방 번호와 user_key, 이미지를 서버로 전송
    room_num_receive = int(request.form['room_num'])
    image_receive = request.form['image']
    user_key_receive = request.form['user_key']

    # 디버그
    print(f"from Unity, animated-image sent : {room_num_receive} {user_key_receive}")

    # 이미지 DB에 입력받은 번호의 방에 유저 키 있을 때 - 기존 정보 변경
    if db.animated_images.find_one({'room_num': room_num_receive, 'user_key': user_key_receive}) != None:
        data_id = db.animated_images.find_one({'room_num': room_num_receive, 'user_key': user_key_receive})['_id']
        db.animated_images.update_one({'_id': data_id}, {'$set': {'image': image_receive}})
        db.animated_images.update_one({'_id': data_id}, {'$set': {'time': time.strftime('%y-%m-%d %H:%M:%S')}})
        print('Animated-image updated success')
        return {"msg": 'Animated-image updated success'}

    # 입력받은 번호의 방과 유저 키 없을 때 - 정보 새로 추가
    else:
        # 유니티에서 받은 방번호, 이미지, 유저 키
        animated_image_list = {
            'room_num': room_num_receive,
            'image': image_receive,
            'user_key': user_key_receive,
            'time': time.strftime('%y-%m-%d %H:%M:%S')
        }
        db.animated_images.insert_one(animated_image_list)
        print('Animated-image inserted success')
        return {"msg": 'Animated-image inserted success'}

# Android: 안드로이드로 유니티를 통해 Animated 된 사진을 전송 (POST) API
@app.route('/image-return', methods=['POST'])
def image_return():
    # 안드로이드는 방 번호를 요청
    room_num_receive = int(request.json['room_num'])

    # DB에 입력받은 번호의 방이 있을 때
    if db.animated_images.find_one({'room_num': room_num_receive}) != None:
        room_image_list = list(db.animated_images.find({'room_num': room_num_receive}))
        # 안드로이드로 전송할 return_json 구성
        # return_json = {
        #     "msg": 'True',
        #     "count": 방에 있는 사람 수,
        #     "0": {"userkey": 유저키, "img": 이미지},
        #     "1": {"userkey": 유저키, "img": 이미지}
        #     "2": {"userkey": 유저키, "img": 이미지}
        #      ... (방에 있는 사람 수 만큼)
        # }
        return_json = {}
        return_json["msg"] = 'True'
        return_json["count"] = len(room_image_list)
        return_json["0"] = room_image_list[0]['image']
        count = 0
        for i in room_image_list:
            return_json[str(count)] = {
                "userkey" : i['user_key'],
                 "img" : i['image']
            }
            count = int(count)
            count += 1

        # 디버그
        print("To Android, Image return success")

        # 앱으로 전송
        return return_json
    # DB에 입력받은 번호의 방이 없을 때
    else:
        print('image-return : No room number')
        return {"msg": 'No room number'}

# ----------------------------------------------------------------------
# 서버 구동
if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)