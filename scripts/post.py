#!/usr/bin/env python3
import os,sys,json,uuid,tempfile,subprocess
import httpx
SUPABASE_URL=os.environ["SUPABASE_URL"]
SUPABASE_KEY=os.environ["SUPABASE_KEY"]
IG_USER_ID=os.environ["IG_USER_ID"]
IG_ACCESS_TOKEN=os.environ["IG_ACCESS_TOKEN"]
TIKTOK_TOKEN=os.environ.get("TIKTOK_ACCESS_TOKEN","")
PLAYER_SLUG=os.environ["PLAYER_SLUG"]
SEARCH_QUERY=os.environ["SEARCH_QUERY"]
WATERMARK=os.environ["WATERMARK_HANDLE"]
SB={"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json"}
def search(q):
 r=subprocess.run(["yt-dlp",f"ytsearch8:{q}","--dump-json","--flat-playlist","--no-playlist","-q"],capture_output=True,text=True,timeout=60)
 out=[]
 for l in r.stdout.strip().splitlines():
  try:
   d=json.loads(l);out.append({"url":d.get("url") or f"https://youtube.com/watch?v={d['id']}","title":d.get("title","")})
  except:pass
 return out
def posted(url):
 r=httpx.get(f"{SUPABASE_URL}/rest/v1/posts",params={"player_slug":f"eq.{PLAYER_SLUG}","source_url":f"eq.{url}","select":"id"},headers=SB,timeout=10)
 return len(r.json())>0
def download(url,out):
 raw=out.replace(".mp4","_raw.mp4")
 dl=subprocess.run(["yt-dlp",url,"-f","best[ext=mp4][height<=1080]/best[ext=mp4]/best","--merge-output-format","mp4","-o",raw,"--no-playlist","-q"],capture_output=True,text=True,timeout=300)
 if dl.returncode!=0 or not os.path.exists(raw):print(f"DL fail:{dl.stderr[:200]}");return False
 probe=subprocess.run(["ffprobe","-v","quiet","-print_format","json","-show_format",raw],capture_output=True,text=True)
 dur=120.0
 try:dur=float(json.loads(probe.stdout)["format"]["duration"])
 except:pass
 start=max(0,min(15,int(dur*0.1)))
 ff=subprocess.run(["ffmpeg","-i",raw,"-ss",str(start),"-t","50","-vf",f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,drawtext=text='@{WATERMARK}':fontsize=42:fontcolor=white:x=30:y=h-90:shadowcolor=black:shadowx=2:shadowy=2","-c:v","libx264","-crf","26","-preset","fast","-c:a","aac","-b:a","128k","-movflags","+faststart",out,"-y","-loglevel","error"],capture_output=True,text=True,timeout=300)
 if ff.returncode!=0 or not os.path.exists(out):print(f"FF fail:{ff.stderr[:200]}");return False
 return True
def upload(fp):
 key=f"{PLAYER_SLUG}/{uuid.uuid4()}.mp4"
 with open(fp,"rb") as f:data=f.read()
 r=httpx.post(f"{SUPABASE_URL}/storage/v1/object/videos/{key}",content=data,headers={**SB,"Content-Type":"video/mp4"},timeout=120)
 if r.status_code not in(200,201):raise RuntimeError(f"Upload fail:{r.text[:100]}")
 return f"{SUPABASE_URL}/storage/v1/object/public/videos/{key}"
def post_ig(vurl,title):
 cap=f"{title}\n#{PLAYER_SLUG} #soccer #football #highlights"
 r=httpx.post(f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",json={"media_type":"REELS","video_url":vurl,"caption":cap,"share_to_feed":True,"access_token":IG_ACCESS_TOKEN},timeout=30)
 r.raise_for_status();cid=r.json()["id"];print(f"Container:{cid}")
 import time
 for _ in range(12):
  time.sleep(10)
  s=httpx.get(f"https://graph.facebook.com/v19.0/{cid}",params={"fields":"status_code","access_token":IG_ACCESS_TOKEN},timeout=15).json()
  print(f"Status:{s.get('status_code')}")
  if s.get("status_code")=="FINISHED":break
 pub=httpx.post(f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",json={"creation_id":cid,"access_token":IG_ACCESS_TOKEN},timeout=30)
 pub.raise_for_status();pid=pub.json()["id"];print(f"IG:{pid}");return pid
def post_tt(vurl,title):
 if not TIKTOK_TOKEN:return ""
 r=httpx.post("https://open.tiktokapis.com/v2/post/publish/video/init/",headers={"Authorization":f"Bearer {TIKTOK_TOKEN}","Content-Type":"application/json; charset=UTF-8"},json={"post_info":{"title":f"{title} #soccer","privacy_level":"PUBLIC_TO_EVERYONE","disable_duet":False,"disable_comment":False,"disable_stitch":False},"source_info":{"source":"PULL_FROM_URL","video_url":vurl}},timeout=30)
 if r.status_code==200:pid=r.json().get("data",{}).get("publish_id","");print(f"TT:{pid}");return pid
 return ""
def log(src,vid,title,ig,tt):
 httpx.post(f"{SUPABASE_URL}/rest/v1/posts",json={"player_slug":PLAYER_SLUG,"source_url":src,"video_url":vid,"title":title,"ig_post_id":ig,"tt_post_id":tt},headers={**SB,"Prefer":"return=minimal"},timeout=10)
def main():
 print(f"Player:{PLAYER_SLUG}")
 res=search(SEARCH_QUERY)
 if not res:sys.exit(0)
 src=title=None
 for r in res:
  if not posted(r["url"]):src,title=r["url"],r["title"];break
 if not src:print("All posted");sys.exit(0)
 print(f"DL:{title}")
 with tempfile.TemporaryDirectory() as d:
  out=f"{d}/processed.mp4"
  if not download(src,out):sys.exit(1)
  vurl=upload(out)
 ig=post_ig(vurl,title)
 tt=post_tt(vurl,title)
 log(src,vurl,title,ig,tt)
 print("Done.")
if __name__=="__main__":main()
