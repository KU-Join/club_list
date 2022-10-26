from http.client import HTTPException
import json
import os
from unicodedata import category
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



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "img")
FEED_IMG_DIR = os.path.join(BASE_DIR, "feed_img")

BACKEND_URL = "http://35.170.94.193"

conn = pymysql.connect(host='localhost', user='root', password='ghkdidakdmf', db='club_list', charset='utf8')
conn.ping(reconnect=True)
cur = conn.cursor()


app = FastAPI()
@app.get("/club-list")
async def get_club_list():
    sql = "SELECT club_id, club_name, club_img, club_description, category, opened, club_URL, leader_id FROM club_list ORDER BY category;"
    cur.execute(sql)
    rows = cur.fetchall()
    rows = group_by_category(rows)
    rows = jsonable_encoder(rows)
    return rows


@app.get("/images/{img_id}")
async def get_img(img_id):
    if not img_id.isalnum() or len(img_id) != 16:
        return {"detail": "Not Found"}
    img_dir = os.path.join(IMG_DIR, img_id + '.jpg')
    if not os.path.isfile(img_dir):
        return {"detail": "Not Found"}
    
    return FileResponse(img_dir)

@app.get("/club-information/{club_id}")
async def get_club_information(club_id):
    sql = f"SELECT club_id, club_name, club_img, club_description, category, opened, club_URL, leader_id FROM club_list WHERE club_id = {club_id};"
    cur.execute(sql)
    rows = cur.fetchall()
    if len(rows) < 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'club_id Not found')
    club_id, club_name, club_img, club_description, category, opened, club_URL, leader_id = rows[0]
    club_dict = {"club_id":club_id, "club_name":club_name, "club_img":club_img, "club_description":club_description, "category":category, "opened":opened, "club_URL":club_URL, "leader_id":leader_id}
    json = jsonable_encoder(club_dict)
    return json

@app.get("/club-feed/{club_id}")
async def get_club_feed(club_id):
    sql = f"SELECT feed_uploader, feed_img, feed_contents, time FROM club_feed WHERE feed_club={club_id} ORDER BY time DESC;"
    cur.execute(sql)
    rows = cur.fetchall()
    json = jsonable_encoder(rows)
    return json

@app.get("/club-feed/images/{img_id}")
async def get_club_feed_img(img_id):
    if not img_id.isalnum() or len(img_id) != 16:
        return {"detail": "Not Found"}
    img_dir = os.path.join(FEED_IMG_DIR, img_id + '.jpg')
    if not os.path.isfile(img_dir):
        return {"detail": "Not Found"}
    
    return FileResponse(img_dir)

@app.get("/registered/{user_id}")
def get_registered_club(user_id: int):
    sql = f"select club_id from club_list where leader_id={user_id}"
    cur.execute(sql)
    result = cur.fetchall()
    if(len(result) == 0):
        return {"club_id": []}
    registered_club = [result[0]]
    return {"club_id": registered_club}
    
@app.post("/club-feed/{club_id}", status_code=status.HTTP_201_CREATED)
def post_club_feed(club_id, club_feed: ClubFeed):
    # feed_id, club_id, uploader_id, time, image_url, contents
    feed_image = club_feed.feed_image
    feed_uploader = club_feed.feed_uploader
    feed_contents = club_feed.feed_contents

    with feed_image.file as img:
        img = Image.open(img)
        img = img.convert("RGB")
        # img.show()
        img_hash = imagehash.phash(img)
        img_path = os.path.join(FEED_IMG_DIR, str(img_hash) + '.jpg')
        img.save(img_path)
    # 중복 제거 구현해야함.
    # if club_name in rows: ~~

    sql = f'INSERT INTO club_feed(feed_club, feed_uploader, feed_contents, feed_img) \
        VALUES(\"{club_id}\", \"{feed_uploader}\", \"{feed_contents}\", \"{BACKEND_URL}/club-feed/images/{img_hash}\");'
    cur.execute(sql)
    conn.commit()
    return



@app.post("/upload-image")
def upload_image_file(club_img: bytes = File(...)):
    img = io.BytesIO(club_img)
    img = Image.open(img)
    img = img.convert("RGB")
    img_hash = imagehash.phash(img)
    # img.save(os.path.join(IMG_DIR, img_hash, '.jpg'))

    return img_hash


@app.post("/club-form", status_code=status.HTTP_201_CREATED)
def upload_club_data(club_name: str = Form(...), club_img: Optional[UploadFile] = None, club_description: str = Form(...), category: str = Form(...), leader_id: int = Form(...)):
# def upload_club_data(data: ClubFormData = Form(...), ):
    # club_name = data.club_name
    # category = data.category
    # club_img = data.club_img
    # club_description = data.club_description
    # leader_id = data.leader_id
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
            VALUES(\"{club_name}\", \"{BACKEND_URL}/images/{img_hash}\", \"{club_description}\", \"{category}\", \"False\", \"{leader_id}\");'
    if not club_img:
        sql = f'INSERT INTO club_list(club_name, club_description, category, opened, leader_id) \
            VALUES(\"{club_name}\", \"{club_description}\", \"{category}\", \"False\", \"{leader_id}\");'

    print(sql)
    cur.execute(sql)
    conn.commit()
    return

@app.put("/club-form/{club_id}",)
def update_club_data(club_id: int, club_name: str = Form(...), club_img: UploadFile = File(...), club_description: str = Form(...), category: str = Form(...), leader_id: int = Form(...)):

    if not len(club_name) < 30:
        return {"detail": "club_name must be shorter than 30"}
    category_list = ["구기체육분과", "레저무예분과", "봉사분과", "어학분과", "연행예술분과", "인문사회분과", "자연과학분과", "종교분과", "창작비평분과", "가등록"]
    if category not in category_list:
        return {"detail": "invalid category."}
    with club_img.file as img:
        img = Image.open(img)
        img = img.convert("RGB")
        # img.show()
        img_hash = imagehash.phash(img)
        img_path = os.path.join(IMG_DIR, str(img_hash) + '.jpg')
        img.save(img_path)
    sql = f'UPDATE club_list SET club_name=\"{club_name}\", club_img=\"{BACKEND_URL}/images/{img_hash}\", club_description=\"{club_description}\", category=\"{category}\", leader_id=\"{leader_id}\" club_URL=\"http://kuclub.com/51566714\" WHERE club_id={club_id};'
    print(sql)
    cur.execute(sql)
    conn.commit()
    
    return 



if __name__ == '__main__':
    eureka_client.init(eureka_server="http://54.180.68.142:8761/", app_name="CLUB-SERVICE", instance_port=80)
    print("eureka_client_initialized")
    uvicorn.run("backend:app", host="0.0.0.0", port = 5005)
    
