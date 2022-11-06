from http.client import HTTPException
import json
import os
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, status, HTTPException
from fastapi.responses import FileResponse
import io
from PIL import Image
import imagehash
import pymysql
from json_utility.sql2json import group_by_category
from fastapi.encoders import jsonable_encoder
import py_eureka_client.eureka_client as eureka_client
from pydantic import BaseModel
from typing import Optional
import pymysqlpool

config={'host':'localhost', 'user':'root', 'password':'ghkdidakdmf', 'database':'club_list', 'autocommit':True}
pool1 = pymysqlpool.ConnectionPool(size=4, maxsize=6, pre_create_num=3, name='pool1', **config)

class ClubFormData(BaseModel):
    club_name: str 
    club_img: UploadFile
    club_description: str
    category: str
    leader_id: int

class ClubFeed(BaseModel):
    feed_uploader: str
    feed_contents: str
    feed_image: UploadFile

class Item_apply(BaseModel):
    club_id:str
    user_id: str

class Item_apply_accept_deny(BaseModel):
    user_id:str = Form(...)
    apply_id:str = Form(...)
    accept:bool = Form(...)




BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "img")
FEED_IMG_DIR = os.path.join(BASE_DIR, "feed_img")

BACKEND_URL = "http://35.170.94.193"

conn = pymysql.connect(host='localhost', user='root', password='ghkdidakdmf', db='club_list', charset='utf8')
conn.ping(reconnect=True)
conn.query('SET GLOBAL connect_timeout=57600')
conn.query('SET GLOBAL wait_timeout=57600')
conn.query('SET GLOBAL interactive_timeout=57600')
cur = conn.cursor()


app = FastAPI()
@app.get("/club-list")
def get_club_list():
    conn = pool1.get_connection()
    cur = conn.cursor()

    sql = "SELECT club_id, club_name, club_img, club_description, category, opened, club_URL, leader_id FROM club_list ORDER BY category;"

    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    rows = group_by_category(rows)
    rows = jsonable_encoder(rows)
    return rows


@app.get("/images/{img_id}")
def get_img(img_id):
    if not img_id.isalnum() or len(img_id) != 16:
        return {"detail": "Not Found"}
    img_dir = os.path.join(IMG_DIR, img_id + '.jpg')
    if not os.path.isfile(img_dir):
        return {"detail": "Not Found"}
    
    return FileResponse(img_dir)

@app.get("/club-information/{club_id}")
def get_club_information(club_id):
    conn = pool1.get_connection()
    cur = conn.cursor()
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    sql = f"SELECT club_id, club_name, club_img, club_description, category, opened, club_URL, leader_id FROM club_list WHERE club_id = {club_id};"
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    if len(rows) < 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'club_id Not found')
    club_id, club_name, club_img, club_description, category, opened, club_URL, leader_id = rows[0]
    club_dict = {"club_id":club_id, "club_name":club_name, "club_img":club_img, "club_description":club_description, "category":category, "opened":bool(opened), "club_URL":club_URL, "leader_id":leader_id}
    json = jsonable_encoder(club_dict)
    return json

@app.get("/club-feed/{club_id}")
def get_club_feed(club_id: str):
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    conn = pool1.get_connection()
    cur = conn.cursor()
    #sql = f'SELECT JSON_ARRAYAGG(JSON_OBJECT("feed_uploader", feed_uploader, "feed_img", feed_img, "feed_contents", feed_contents, "time", time)) FROM club_feed WHERE club_id={club_id} ORDER BY time DESC;'
    sql = f'SELECT feed_uploader, feed_img , feed_contents, time FROM club_feed WHERE club_id={club_id} ORDER BY time DESC;'
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    
    feed_list = list()
    for feed in rows:
        feed_uploader, feed_img , feed_contents, time = feed
        feed_dict = {'feed_uploader':feed_uploader, 'feed_img': feed_img, 'feed_contents': feed_contents, 'time': time}
        feed_list.append(feed_dict)
    json = jsonable_encoder(feed_list)
    return json

@app.get("/club-feed/images/{img_id}")
def get_club_feed_img(img_id):
    if not img_id.isalnum() or len(img_id) != 16:
        return {"detail": "Not Found"}
    img_dir = os.path.join(FEED_IMG_DIR, img_id + '.jpg')
    if not os.path.isfile(img_dir):
        return {"detail": "Not Found"}
    
    return FileResponse(img_dir)

@app.get("/registered/{user_id}")
def get_registered_club(user_id: str):
    conn = pool1.get_connection()
    cur = conn.cursor()
    sql = f"SELECT club_id, club_name, leader from club_member where user_id=\"{user_id}\""
    cur.execute(sql)
    result = cur.fetchall()
    conn.close()
    if(len(result) == 0):
        return {"club_id": []}
    registered_clubs = []
    for club in result:
        registered_clubs.append({"club_id":club[0], "club_name":club[1], "leader": bool(club[2])})
    return jsonable_encoder(registered_clubs)

@app.get("/registered/{user_id}/{club_id}")
def get_registered_club_user(user_id: str, club_id: str):
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    sql = f"SELECT leader FROM club_member WHERE club_id={int(club_id)} and user_id=\"{user_id}\";"
    conn = pool1.get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    conn.close()
    if len(result) == 0:
        return jsonable_encoder({'member': False, 'leader': False})
    else:
        return jsonable_encoder({'member': True, 'leader': bool(result[0][0])})


@app.get("/club-apply/{club_id}")
def get_club_apply(club_id: str, user_id:str):
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    conn = pool1.get_connection()
    cur = conn.cursor()
    sql = f"SELECT club_id, leader_id FROM club_list WHERE club_id = {club_id};"
    cur.execute(sql)
    result = cur.fetchall()
    if (len(result) == 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id {club_id} does not exist.")
    
    leader_id = result[0][1]
    if (str(leader_id) != str(user_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"user_id {user_id} is not leader of club_id {club_id}.")
    sql = f"SELECT apply_id, club_id, user_id, club_name FROM club_apply WHERE club_id=\"{club_id}\""
    cur.execute(sql)
    result = cur.fetchall()
    conn.close()
    application_list = list()
    if (len(result) == 0):
        return application_list
    for application in result:
        apply_id, club_id, user_id, club_name = application
        apply_dict = {"apply_id":str(apply_id), "club_name": str(club_name), "club_id":str(club_id), "user_id": str(user_id)}
        application_list.append(apply_dict)
    return jsonable_encoder(application_list)
        
@app.get("/club-member/{club_id}")
def get_club_member(club_id:str):
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = "club_id must be number")
    sql = f"SELECT user_id, leader FROM club_member WHERE club_id = {int(club_id)}"
    conn = pool1.get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    conn.close()

    member_list = list()
    if len(result) == 0 :
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = "club is empty")
    for member in result:
        user_id = str(member[0])
        leader = bool(member[1])
        dic = {"user_id":user_id, "leader":leader}
        member_list.append(dic)
    return jsonable_encoder(member_list)



    



@app.delete("/club-list/{club_id}")
def delete_club(club_id:str, password:str):
    if not password == "7777":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"wrong password")
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    sql = f"SELECT club_id FROM club_list WHERE club_id = {int(club_id)}"
    conn = pool1.get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    if len(result) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detal=f"club_id {club_id} does not exist")
    sql = f"DELETE FROM club_feed WHERE club_id = {int(club_id)}"
    cur.execute(sql)
    sql = f"DELETE FROM club_member WHERE club_id = {int(club_id)}"
    cur.execute(sql)
    sql = f"DELETE FROM club_feed WHERE club_id = {int(club_id)}"
    cur.execute(sql)
    sql = f"DELETE FROM club_list WHERE club_id = {int(club_id)}"
    cur.execute(sql)
    conn.close()


    

@app.delete("/club-apply/{club_id}")
def apply_accept_deny(club_id: str,  item: Item_apply_accept_deny):
    user_id = item.user_id
    apply_id = item.apply_id
    accept = item.accept

    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    if not apply_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"apply_id must be number")
    sql = f"SELECT club_id, leader_id, club_name FROM club_list WHERE club_id = {club_id};"
    conn = pool1.get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    if (len(result) == 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id {club_id} does not exist.")
    leader_id = result[0][1]
    club_name = result[0][2]
    if (str(leader_id) != str(user_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"user_id {user_id} is not leader of club_id {club_id}.")
    sql = f"SELECT apply_id, club_id, user_id, club_name FROM club_apply WHERE apply_id={int(apply_id)};"
    cur.execute(sql)
    result = cur.fetchall()
    if len(result) == 0:    
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"apply_id {apply_id} does not exist")
    apply_id, club_id, user_id, club_name = result[0]
    if accept:
        if is_member(str(club_id), user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"user_id {user_id} is already member of club_id {club_id}.")
        sql = f"INSERT INTO club_member(club_id, club_name, user_id, leader) VALUES ({int(club_id)}, \"{str(club_name)}\", \"{str(user_id)}\", 0);"
        cur.execute(sql)
    sql = f"DELETE from club_apply where apply_id = {int(apply_id)};"
    print(sql)
    cur.execute(sql)
    conn.commit()
    conn.close()
     
@app.post("/club-apply/", status_code=status.HTTP_201_CREATED)
def apply_club(item :Item_apply):
    club_id = item.club_id
    user_id = item.user_id
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    sql = f"SELECT club_id, club_name FROM club_list WHERE club_id = {club_id};"
    conn = pool1.get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    
    if (len(result) == 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id {club_id} does not exist.")
    club_name = result[0][1]
    if (is_member(club_id = str(club_id), user_id = user_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already member of the club")
    
    sql = f"INSERT INTO club_apply (club_id, user_id, club_name) VALUES ({int(club_id)}, \"{str(user_id)}\", \"{str(club_name)}\");"
    cur.execute(sql)
    conn.commit()
    conn.close()

def is_member(club_id: str, user_id: str):
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    sql = f"SELECT club_id, user_id, leader FROM club_member WHERE club_id={int(club_id)} and user_id=\"{str(user_id)}\";"
    conn = pool1.get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    conn.close()
    if len(result) == 0:
        return False
    return True

@app.post("/club-feed/{club_id}", status_code=status.HTTP_201_CREATED)
def post_club_feed(club_id:str, feed_uploader:str = Form(...), feed_contents:str = Form(...), feed_image:Optional[UploadFile] = None):
    # feed_id, club_id, uploader_id, time, image_url, contents
    # feed_image = club_feed.feed_image
    # feed_uploader = club_feed.feed_uploader
    # feed_contents = club_feed.feed_contents
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    if feed_image:
        with feed_image.file as img:
            img = Image.open(img)
            img = img.convert("RGB")
            # img.show()
            img_hash = imagehash.phash(img)
            img_path = os.path.join(FEED_IMG_DIR, str(img_hash) + '.jpg')
            img.save(img_path)
        sql = f'INSERT INTO club_feed(club_id, feed_uploader, feed_contents, feed_img) \
        VALUES(\"{club_id}\", \"{feed_uploader}\", \"{feed_contents}\", \"{BACKEND_URL}/club-feed/images/{img_hash}\");'
    if not feed_image:
        sql = f'INSERT INTO club_feed(club_id, feed_uploader, feed_contents) \
        VALUES(\"{club_id}\", \"{feed_uploader}\", \"{feed_contents}\");'

    conn = pool1.get_connection()
    cur = conn.cursor()
    
    cur.execute(sql)
    conn.commit()
    conn.close()



@app.post("/upload-image")
def upload_image_file(club_img: bytes = File(...)):
    img = io.BytesIO(club_img)
    img = Image.open(img)
    img = img.convert("RGB")
    img_hash = imagehash.phash(img)
    # img.save(os.path.join(IMG_DIR, img_hash, '.jpg'))

    return img_hash

def is_exist_club(club_name:str):
    sql = f"SELECT EXISTS (SELECT club_id FROM club_list WHERE club_name=\"{club_name}\" LIMIT 1) AS SUCCESS;"
    conn = pool1.get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    conn.close()
    exist = result[0][0]
    if exist:
        return True
    return False


@app.post("/club-form", status_code=status.HTTP_201_CREATED)
def upload_club_data(club_name: str = Form(...), club_img: Optional[UploadFile] = None, club_description: str = Form(...), category: str = Form(...), leader_id: str = Form(...)):
# def upload_club_data(data: ClubFormData = Form(...), ):
    # club_name = data.club_name
    # category = data.category
    # club_img = data.club_img
    # club_description = data.club_description
    # leader_id = data.leader_id
    if is_exist_club(club_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_name {club_name} is already exists.")
    if not len(club_name) < 30:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The club_name is too long. It must be shorter than 30 characters")
    category_list = ["구기체육분과", "레저무예분과", "봉사분과", "어학분과", "연행예술분과", "인문사회분과", "자연과학분과", "종교분과", "창작비평분과", "가등록"]
    if category not in category_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'The category is wrong. Category includes {category_list}')
    if club_img:
        with club_img.file as img:
            img = Image.open(img)
            img = img.convert("RGB")
            # img.show()
            img_hash = imagehash.phash(img)
            img_path = os.path.join(IMG_DIR, str(img_hash) + '.jpg')
            img.save(img_path)
    # 중복 제거 구현해야함.
    # if club_name in rows: ~~
    if club_img:
        sql = f'INSERT INTO club_list(club_name, club_img, club_description, category, opened, leader_id) \
            VALUES(\"{club_name}\", \"{BACKEND_URL}/images/{img_hash}\", \"{club_description}\", \"{category}\", 1, \"{leader_id}\");'
    if not club_img:
        sql = f'INSERT INTO club_list(club_name, club_description, category, opened, leader_id) \
            VALUES(\"{club_name}\", \"{club_description}\", \"{category}\", 1, \"{leader_id}\");'
    conn = pool1.get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    sql = "SELECT LAST_INSERT_ID()"
    cur.execute(sql)
    club_id = cur.fetchall()[0][0]
    sql = f"INSERT INTO club_member(club_id, club_name, user_id, leader) VALUES({int(club_id)}, \"{str(club_name)}\", \"{str(leader_id)}\", {int(True)});"
    cur.execute(sql)
    conn.commit()
    conn.close()

@app.post("/update-club-form/{club_id}")
def update_club_data(club_id: str, club_name: str = Form(...), club_img: Optional[UploadFile] = None, club_description: str = Form(...), category: str = Form(...), leader_id: str = Form(...), opened: bool = Form(...)):
    if not club_id.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"club_id must be number")
    if not len(club_name) < 30:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The club_name is too long. It must be shorter than 30 characters")
    category_list = ["구기체육분과", "레저무예분과", "봉사분과", "어학분과", "연행예술분과", "인문사회분과", "자연과학분과", "종교분과", "창작비평분과", "가등록"]
    if category not in category_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'The category is wrong. Category includes {category_list}')
    if not is_member(int(club_id), leader_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"leader_id {leader_id} is not member of club_id {club_id}")
    if club_img:
        with club_img.file as img:
            img = Image.open(img)
            img = img.convert("RGB")
            # img.show()
            img_hash = imagehash.phash(img)
            img_path = os.path.join(IMG_DIR, str(img_hash) + '.jpg')
            img.save(img_path)
        sql = f'UPDATE club_list SET club_name=\"{club_name}\", club_img=\"{BACKEND_URL}/images/{img_hash}\", club_description=\"{club_description}\", category=\"{category}\", leader_id=\"{leader_id}\", opened={int(opened)}  WHERE club_id={int(club_id)};'
    if not club_img:
        sql = f'UPDATE club_list SET club_name=\"{club_name}\", club_description=\"{club_description}\", category=\"{category}\", leader_id=\"{leader_id}\", opened={int(opened)} WHERE club_id={int(club_id)};'
    conn = pool1.get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    sql = f"UPDATE club_member SET leader=0 WHERE club_id={int(club_id)} and leader=1;"
    cur.execute(sql)
    sql = f"UPDATE club_member SET leader=1 WHERE club_id={int(club_id)} and user_id=\"{str(leader_id)}\";"
    cur.execute(sql)
    sql = f"UPDATE club_member SET club_name=\"{str(club_name)}\" WHERE club_id={int(club_id)};"
    cur.execute(sql)
    conn.commit()
    conn.close()

    


if __name__ == '__main__':
    eureka_server = "http://54.180.68.142:8761/eureka"
    eureka_response = eureka_client.init(eureka_server=eureka_server, app_name="CLUB-SERVICE", instance_port=80, instance_ip="35.170.94.193")
    uvicorn.run("backend:app", host="172.31.29.143", port = 5005)
    
