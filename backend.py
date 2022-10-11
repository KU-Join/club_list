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


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "img")

BACKEND_URL = "http://3.85.92.73"

conn = pymysql.connect(host='localhost', user='ec2_club_list', password='ghkdidehd', db='club_list', charset='utf8')
cur = conn.cursor()

app = FastAPI()
@app.get("/club-list")
async def get_club_list():
    sql = "SELECT * FROM club_list ORDER BY category"
    cur.execute(sql)
    rows = cur.fetchall()
    print(rows)
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

    
@app.post("/upload-image")
def upload_image_file(club_img: bytes = File(...)):
    img = io.BytesIO(club_img)
    img = Image.open(img)
    img = img.convert("RGB")
    img_hash = imagehash.phash(img)
    # img.save(os.path.join(IMG_DIR, img_hash, '.jpg'))

    return img_hash

@app.post("/club-form")
def upload_club_data(club_name: str = Form(...), club_img: UploadFile = File(...), club_description: str = Form(...), category: str = Form(...)):
    if not isalnum(club_name):
        return {"detail": "Not Found"}
    if not len(club_name) < 30:
        return {"detail": "Not Found"}

    with club_img.file as img:
        img = Image.open(img)
        img = img.convert("RGB")
        # img.show()
        img_hash = imagehash.phash(img)
        img_path = os.path.join(IMG_DIR, str(img_hash) + '.jpg')
        img.save(img_path)


    # 중복 제거 구현해야함.
    # if club_name in rows: ~~

    sql = f'INSERT INTO club_list(club_name, club_img, club_description, category, opened, club_URL) \
        VALUES(\"{club_name}\", \"{BACKEND_URL}/images/{img_hash}\", \"{club_description}\", \"{category}\", \"False\", \"http://kuclub.com/51566714\");'
    print(sql)
    cur.execute(sql)
    conn.commit()
    return

@app.post("/update_club_form/{club_id}")
def update_club_form(club_id: int, club_name: str = Form(...), club_img: UploadFile = File(...), club_description: str = Form(...), category: str = Form(...)):

   
    with club_img.file as img:
        img = Image.open(img)
        img = img.convert("RGB")
        # img.show()
        img_hash = imagehash.phash(img)
        img_path = os.path.join(IMG_DIR, str(img_hash) + '.jpg')
        img.save(img_path)
    sql = f'UPDATE club_list SET club_name=\"{club_name}\", club_img=\"{BACKEND_URL}/images/{img_hash}\", club_description=\"{club_description}\", category=\"{category}\", club_URL=\"http://kuclub.com/51566714\" WHERE club_id={club_id}'
    print(sql)
    cur.execute(sql)
    conn.commit()
    
    return 



if __name__ == '__main__':
    uvicorn.run("backend:app", host="0.0.0.0", port = 5005, reload = True)
