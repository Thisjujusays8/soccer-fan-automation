#!/usr/bin/env python3
import os,sys,json,uuid,time,tempfile,subprocess,urllib.request,urllib.parse

SUPABASE_URL=os.environ['SUPABASE_URL']
SUPABASE_KEY=os.environ['SUPABASE_KEY']
IG_USER_ID=os.environ.get('IG_USER_ID','')
IG_TOKEN=os.environ.get('IG_ACCESS_TOKEN','')
TIKTOK_TOKEN=os.environ.get('TIKTOK_ACCESS_TOKEN','')
PLAYER_SLUG=os.environ['PLAYER_SLUG']
SEARCH_QUERY=os.environ['SEARCH_QUERY']
WATERMARK=os.environ['WATERMARK_HANDLE']

SB={'apikey':SUPABASE_KEY,'Authorization':f'Bearer {SUPABASE_KEY}','Content-Type':'application/json'}

def sb_get(path,params=''):
    req=urllib.request.Request(f'{SUPABASE_URL}/rest/v1/{path}?{params}',headers=SB)
    with urllib.request.urlopen(req) as r:return json.loads(r.read())

def sb_post(path,data):
    h={**SB,'Prefer':'return=minimal'}
    req=urllib.request.Request(f'{SUPABASE_URL}/rest/v1/{path}',data=json.dumps(data).encode(),headers=h)
    with urllib.request.urlopen(req) as r:return r.status

def http_post(url,data,headers=None):
    h={'Content-Type':'application/json',**(headers or {})}
    req=urllib.request.Request(url,data=json.dumps(data).encode(),headers=h)
    with urllib.request.urlopen(req) as r:return json.loads(r.read())

def search_youtube(query):
    r=subprocess.run(['yt-dlp',f'ytsearch8:{query}','--dump-json','--flat-playlist','--no-playlist','-q',
        '--extractor-args','youtube:player_client=ios'],capture_output=True,text=True,timeout=60)
    results=[]
    for line in r.stdout.strip().splitlines():
        try:
            d=json.loads(line)
            results.append({'url':d.get('url') or f"https://www.youtube.com/watch?v={d['id']}",
                           'title':d.get('title','')})
        except:continue
    return results

def already_posted(url):
    rows=sb_get('posts',f'player_slug=eq.{PLAYER_SLUG}&source_url=eq.{urllib.parse.quote(url)}&select=id')
    return len(rows)>0

def download_and_process(source_url,tmpdir):
    raw=os.path.join(tmpdir,'raw.mp4')
    out=os.path.join(tmpdir,'out.mp4')
    dl=subprocess.run(['yt-dlp',source_url,'-f','best[ext=mp4][height<=1080]/best',
        '-o',raw,'--merge-output-format','mp4','--no-playlist','-q',
        '--extractor-args','youtube:player_client=ios'],
        capture_output=True,text=True,timeout=300)
    if dl.returncode!=0:raise RuntimeError(f'Download failed: {dl.stderr[:200]}')
    probe=subprocess.run(['ffprobe','-v','quiet','-print_format','json','-show_format',raw],
        capture_output=True,text=True)
    try:start=max(0,min(10,int(float(json.loads(probe.stdout)['format']['duration'])*0.1)))
    except:start=10
    ff=subprocess.run(['ffmpeg','-i',raw,'-ss',str(start),'-t','50',
        '-vf',f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,drawtext=text='@{WATERMARK}':fontsize=42:fontcolor=white:x=30:y=h-90:shadowcolor=black:shadowx=2:shadowy=2",
        '-c:v','libx264','-crf','26','-preset','fast','-c:a','aac','-b:a','128k',
        '-movflags','+faststart',out,'-y','-loglevel','error'],
        capture_output=True,text=True,timeout=300)
    if ff.returncode!=0:raise RuntimeError(f'FFmpeg failed: {ff.stderr[:200]}')
    return out

def upload_storage(filepath):
    key=f'{PLAYER_SLUG}/{uuid.uuid4()}.mp4'
    with open(filepath,'rb') as f:data=f.read()
    req=urllib.request.Request(f'{SUPABASE_URL}/storage/v1/object/videos/{key}',
        data=data,headers={**SB,'Content-Type':'video/mp4'})
    with urllib.request.urlopen(req):pass
    return f'{SUPABASE_URL}/storage/v1/object/public/videos/{key}'

def post_instagram(video_url,caption):
    if not IG_USER_ID or not IG_TOKEN:
        print('  IG: no credentials, skipping');return ''
    base='https://graph.facebook.com/v19.0'
    c=http_post(f'{base}/{IG_USER_ID}/media',
        {'media_type':'REELS','video_url':video_url,'caption':caption,'share_to_feed':True,'access_token':IG_TOKEN})
    print(f'  IG container: {c["id"]} - waiting 60s...')
    time.sleep(60)
    p=http_post(f'{base}/{IG_USER_ID}/media_publish',{'creation_id':c['id'],'access_token':IG_TOKEN})
    return p.get('id','')

def post_tiktok(video_url,title):
    if not TIKTOK_TOKEN:return ''
    r=http_post('https://open.tiktokapis.com/v2/post/publish/video/init/',
        {'post_info':{'title':title,'privacy_level':'PUBLIC_TO_EVERYONE','disable_duet':False,'disable_comment':False},
         'source_info':{'source':'PULL_FROM_URL','video_url':video_url}},
        headers={'Authorization':f'Bearer {TIKTOK_TOKEN}','Content-Type':'application/json; charset=UTF-8'})
    return r.get('data',{}).get('publish_id','')

def main():
    print(f'[{PLAYER_SLUG}] Starting')
    results=search_youtube(SEARCH_QUERY)
    if not results:print('No results');sys.exit(0)
    source_url=next((r['url'] for r in results if not already_posted(r['url'])),None)
    if not source_url:print('All clips already posted');sys.exit(0)
    title=next(r['title'] for r in results if r['url']==source_url)
    print(f'  New clip: {title}')
    with tempfile.TemporaryDirectory() as tmp:
        out=download_and_process(source_url,tmp)
        print(f'  Processed ({os.path.getsize(out)//1024}KB), uploading...')
        video_url=upload_storage(out)
    print(f'  Stored: {video_url}')
    ig_id=post_instagram(video_url,f'{title} ⚽ #{PLAYER_SLUG} #soccer #football #highlights')
    if ig_id:print(f'  IG: {ig_id}')
    tt_id=post_tiktok(video_url,f'{title} ⚽ #soccer #football')
    if tt_id:print(f'  TikTok: {tt_id}')
    sb_post('posts',{'player_slug':PLAYER_SLUG,'source_url':source_url,'video_url':video_url,
        'title':title,'ig_post_id':ig_id,'tt_post_id':tt_id})
    print(f'[{PLAYER_SLUG}] Done!')

if __name__=='__main__':main()
