# import
from google.cloud import storage
import os
import time
from selenium import webdriver
from bs4 import BeautifulSoup
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# client
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "blob-storage-gcp-bc807e0adb48.json"
storage_client = storage.Client()

# list blobs in bucket
def list_blobs(bucket_name):
    blobs_list = storage_client.list_blobs(bucket_name)
    blobs_list = [blob.name for blob in blobs_list]
    return blobs_list

# empty bucket
def empty_bucket(bucket_name):
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    for blob in blobs: blob.delete()

# url > content > blob
def upload_url_blob(url, bucket_name, blob_name):
    image_data = requests.get(url).content
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_data, content_type = "image/jpg")

# identical blobs
def compare_blobs(bucket_name1, blob_name1, bucket_name2, blob_name2):
    bucket1, bucket2 = storage_client.bucket(bucket_name1), storage_client.bucket(bucket_name2)
    image1, image2 = bucket1.get_blob(blob_name1), bucket2.get_blob(blob_name2)
    if image1.md5_hash == image2.md5_hash: return True
    else: return False

# download blob
def download_blob(bucket_name, source_blob_name, destination_file_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

# afresh
empty_bucket("bucket_packshots_new")
empty_bucket("bucket_packshots_present")

# existing packshots
packshots_historical = list_blobs("bucket_packshots_historical")

# open window
options = webdriver.ChromeOptions().add_argument("ignore-certificate-errors")
driver = webdriver.Chrome(options = options)
driver.maximize_window()

# link
pg = 0
while(1): 
    pg = pg + 1
    link = "https://ushopbd.com/collections/international/all?page=" + str(pg) + "&view=list"
    driver.get(link)

    # soup
    soup_init = BeautifulSoup(driver.page_source, "html.parser")
    soup = soup_init.find_all("img", attrs = {"class": "list-view-item__image"})

    # page
    sku_count = len(soup)
    if sku_count == 0: break
    print("Scraping from page: " + str(pg))
    
    # scrape
    for i in range(0, sku_count):
        
        # url
        try: url = "https:" + soup[i]["src"]
        except: continue

        # filename
        packshot_now = "packshot_" + time.strftime("%d-%b-%y") + "_pg_" + str(pg) + "_sl_" + str(i + 1) + ".jpg"

        # upload to present
        upload_url_blob(url, "bucket_packshots_present", packshot_now)

        # check if new
        if_found = 0
        for packshot_old in packshots_historical:
            if compare_blobs("bucket_packshots_historical", packshot_old, "bucket_packshots_present", packshot_now):
                if_found = 1
                break

        # record if new
        if if_found == 0: 
            print("New packshot: " + url)
            upload_url_blob(url, "bucket_packshots_new", packshot_now)
            upload_url_blob(url, "bucket_packshots_historical", packshot_now)
            download_blob("bucket_packshots_new", packshot_now, packshot_now)

# close window
driver.close()

# email
sender_email = "shithi30@gmail.com"
recivr_email = ["shithi30@outlook.com"]

# object
msg = MIMEMultipart()
msg["Subject"] = "USHOP Packshots"
msg["From"] = "Shithi Maitra"
msg["To"] = ", ".join(recivr_email)

# body
body = '''New packshots identified, please see attachments.<br><br>Thanks,<br>Shithi Maitra<br>Ex Asst. Manager, CS Analytics<br>Unilever BD Ltd.<br>'''
msg.attach(MIMEText(body, "html"))

# attach
files_to_attach = [filename for filename in os.listdir() if filename.endswith(".jpg")]
for file_path in files_to_attach:
    part = MIMEBase("application", "octet-stream")
    with open(file_path, "rb") as attachment: part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(file_path)}")
    msg.attach(part)

# send
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(sender_email, "uhfu cppa sxgh bwpr")
    if len(files_to_attach) > 0: server.sendmail(sender_email, recivr_email, msg.as_string())
