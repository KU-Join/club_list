import json
import os
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
import io
from PIL import Image
import imagehash
import pymysql
from json_utility.sql2json import sql2json, group_by_category
from fastapi.encoders import jsonable_encoder


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE_DIR, "img/")

BACKEND_URL = "http://localhost:8000/"

conn = pymysql.connect(host='localhost', user='fastapi', password='7478', db='club_list', charset='utf8')
cur = conn.cursor()

app = FastAPI()
@app.get("/clubs-lists/")
async def get_club_list():
    sql = "SELECT * FROM club_list ORDER BY category"
    cur.execute(sql)
    rows = cur.fetchall()
    rows = group_by_category(rows)
    rows = jsonable_encoder(rows)
    return rows


@app.get("/images/{img_id}")
async def get_img(img_id):
    img_dir = './img/' + img_id + '.jpg'
    return FileResponse(img_dir)

    
@app.post("/upload-image")
def upload_image_file(club_img: bytes = File(...)):
    img = io.BytesIO(club_img)
    img = Image.open(img)
    img = img.convert("RGB")
    img_hash = imagehash.phash(img)
    img.save(os.path.join(IMG_DIR, img_hash, '.jpg'))

    return img_hash

@app.post("/club-form")
def upload_club_data(club_name: str = Form(...), club_img: bytes = File(...), club_description: str = Form(...), category: str = Form(...)):
    img = io.BytesIO(club_img)
    img = Image.open(img)
    img = img.convert("RGB")
    img_hash = imagehash.phash(img)
    img_path = os.path.join(IMG_DIR, img_hash, '.jpg')
    img.save(img_path)

    sql = "SELECT club_name FROM club_list"
    cur.execute(sql)
    rows = cur.fetchall()
    # 중복 제거 구현해야함.
    # if club_name in rows: ~~

    sql = f'INSERT INTO club_list(club_name, club_img, club_description, category, opened, club_URL) \
        VALUES({club_name}, "{BACKEND_URL}/images/{img_path}", "{club_description}", "{category}", "False", "http://kuclub.com/51566714")'
    

    return

if __name__ == '__main__':
    uvicorn.run("backend:app", host="localhost", port = 8000, reload = True)