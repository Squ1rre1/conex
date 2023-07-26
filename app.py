import streamlit as st
import googleapiclient.discovery
import streamlit.components.v1 as components
import utils
import pandas as pd
import urllib.parse, urllib.request
from urllib import parse
from youtube_transcript_api import YouTubeTranscriptApi
import json
import queue
import re

# 유튜브 검색시 유튜브 리스트 저장
class YoutubeVideo:
    youtube_list = list()
    def __init__(self,name,url,desc,duration):
        self.name=name
        self.url=url
        self.desc=desc
        self.duration=duration
        self.watch=None
        self.segment=None
        self.youtube_list.append(self)
    
    @classmethod
    def list_reset(cls):
        cls.youtube_list.clear()

class Script_Exctractor:
    def __init__(self,vid):
        self.vid = vid
        self.scriptData:list = []
        self.setTime = 600
        self.wikiUserKey = "ecnkjsfhuuvmjfxdvdziepjwznhwdc"

    # youtube script 추출
    def Extract(self):
        # youtube script 받아오기 위한 url 전처리부분
        parsedUrl = parse.urlparse(self.vid)
        vid = parse.parse_qs(parsedUrl.query)['v'][0]
        languages = ['en','en-US']
        str:list = YouTubeTranscriptApi.get_transcript(vid,languages)

        # 저장된 json정보를 timeSet단위에 맞게 분리
        ret = queue.Queue()
        nowSec = self.setTime
        sentence = ''
        for st in str:
            if st['start'] >= nowSec:
                ret.put(sentence)
                sentence = ''
                nowSec += self.setTime
                if frontSt['start'] + frontSt['duration'] >= nowSec:
                    sentence += frontSt['text'] + '\n'
            sentence += st['text'] + '\n'
            frontSt = st
        ret.put(sentence)
        while not ret.empty():
            self.scriptData.append(ret.get())
        print("done")

        for i in range(len(self.scriptData)):
            text = self.scriptData[i].replace(u'\xa0', u' ').replace(u'\n',u' ').replace(u'  ',u' ')
            self.scriptData[i] = text

    def CallWikifier(self, text, lang="en", threshold=0.8, numberOfKCs=5):
        # Prepare the URL.
        data = urllib.parse.urlencode([
                ("text", text), ("lang", lang),
                ("userKey", self.wikiUserKey),
                ("pageRankSqThreshold", "%g" % threshold),
                ("applyPageRankSqThreshold", "true"),
                ("nTopDfValuesToIgnore", "200"),
                ("nWordsToIgnoreFromList", "200"),
                ("wikiDataClasses", "false"),
                ("wikiDataClassIds", "false"),
                ("support", "false"),
                ("ranges", "false"),
                ("minLinkFrequency", "3"),
                ("includeCosines", "false"),
                ("maxMentionEntropy", "2")
                ])
        url = "http://www.wikifier.org/annotate-article"
        # Call the Wikifier and read the response.
        req = urllib.request.Request(url, data=data.encode("utf8"), method="POST")
        with urllib.request.urlopen(req, timeout = 60) as f:
            response = f.read()
            response = json.loads(response.decode("utf8"))

        sorted_data = sorted(response['annotations'], key=lambda x: x['pageRank'], reverse=True)
        # Output the annotations.
        num = 0
        result = []
        for annotation in sorted_data:
            if num < numberOfKCs:
                print("%s (%s) %s" % (annotation["title"], annotation["url"], annotation['pageRank']))
                result.append({"title":annotation["title"],"url":annotation["url"],"pageRank":annotation["pageRank"]})

            num += 1

        res = result
        result = []
        return res

    def UrltoWiki(self):
        self.Extract()

        number = 1
        results = []
        for text in self.scriptData:
            print(f"{number}st segemnt")
            results.append(self.CallWikifier(text))
            number += 1

        wiki_data = pd.DataFrame()
        seg_no = 1
        print(results)

        for seg_item in results:
            seg_index = range(0,len(seg_item))
            seg_df = pd.DataFrame(seg_item,index = seg_index)
            seg_df['seg_no'] = seg_no
            wiki_data = pd.concat([wiki_data,seg_df])
            seg_no = seg_no + 1
        return wiki_data

YOUTUBE_API_KEY = "AIzaSyCt74iOovLdzJMGCfsCAW4nAssQB8LJWo0"

# API client library

# API information
api_service_name = "youtube"
api_version = "v3"
# API client
youtube = googleapiclient.discovery.build(
    api_service_name, api_version, developerKey = YOUTUBE_API_KEY)

# Page config
st.set_page_config(page_title="CONEX: CONcept EXploration Unleashed", layout="wide")

# sidbar
with st.sidebar:
    st.markdown("# CONEX: CONcept EXploration Unleashed")
    st.write("Swimming in the vast sea of nline lectures")
    st.markdown("## About")
    st.markdown("**CONEX** aids in the continuous exploration of specialized concept(a.k.a knowledge) that is yet unfamiliar, derived from a vast amount of online lectures.")
    st.markdown("## Features")
    st.markdown(""" 
                    - allows learners to easily and quickly access new concepts related to the specialized knowledge within lectures
                    - assists in understanding their definitions on Wikipedia
                    - provides pre-filtered lectures to identify concepts that are not learned yet
                    - enables learners to catch those concepts in other lectures""")
    st.markdown("---")
    st.markdown("너가 학습한 개념")
    st.markdown("---")
    st.markdown("@ 2023 Data science labs, Dong-A University, Korea.")

# get search text
def get_text():
    input_text = st.text_input("Search for courses to explore unfamiliar concepts", value="Recommendation System", key="input")
    return input_text

def duration_to_minutes(duration_str):
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration_str)
    if not match:
        return 0

    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0

    total_minutes = hours * 60 + minutes
    return total_minutes

def search_youtubes(query):
    VIDEO_COUNT=10 # 유튜브에서 들고 올 영상 수
    PREFIX_YOUTUBE_URL = "https://www.youtube.com/watch?v="
    YoutubeVideo.list_reset()
    
    request = youtube.search().list(
        part="id,snippet",
        type='video',
        q= query,
        videoDefinition='high',
        maxResults=VIDEO_COUNT,
        fields="items(id(videoId),snippet(publishedAt,channelId,channelTitle,title,description))"
    )

    response = request.execute()
    video_items = response.get('items', [])

    # 유튜브 리스트 객체 생성
    for item in video_items:
        video_id = item['id']['videoId']
        # 영상 길이 받아오는 쿼리
        video_request = youtube.videos().list(
            part='contentDetails',
            id=video_id
        )
        video_response = video_request.execute()
        duration = video_response['items'][0]['contentDetails']['duration']
        duration = duration_to_minutes(duration)
        if(duration>9 and duration<120): # 영상 길이가 9분초과 120분 미만으로만 저장
            name = item['snippet']['title']
            url = PREFIX_YOUTUBE_URL + item['id']['videoId']
            desc = utils.truncate_text ( item['snippet']['description'] )
            video_init = YoutubeVideo(name=name,url=url,desc=desc,duration=duration)
    
    #test
    #print(YoutubeVideo.youtube_list[0].url)
    return YoutubeVideo.youtube_list


# extract_concepts
def extract_concepts(vid):
    segment_text = ""

    concepts = st.markdown(f"""
                    <div class="overlay-layer">
                        <div class="box">
                            <a href="LINK_URL"><div class="circle" id="circle1"></div></a>
                            <a href="LINK_URL"><div class="circle" id="circle2"></div></a>
                            <a href="LINK_URL"><div class="circle" id="circle3"></div></a>
                            <a href="LINK_URL"><div class="circle" id="circle4"></div></a>
                            <a href="LINK_URL"><div class="circle" id="circle5"></div></a>
                        </div>
                    </div>""", unsafe_allow_html=True )
    return concepts

user_input = get_text()

if user_input:
    video_list = search_youtubes(user_input) # 검색한 영상 받아온 리스트    # video_list 변수는 사용하진 않지만 가비지 컬렉터가 안돌도록 저장
    print(len(YoutubeVideo.youtube_list))
    # 위키화 및 랭크
    for index, video in enumerate(YoutubeVideo.youtube_list):
        try:
            Scripts = Script_Exctractor(video.url)
            video.segment = Scripts.UrltoWiki()
            print(video.segment)
        except Exception as ex:
            print(ex)
            print(f"{index}번째 영상 삭제")
            YoutubeVideo.youtube_list.pop(index)

# 페이지 1, 2, 3 
tab1, tab2, tab3 = st.tabs(["New Learning", "Uncomprehended", "Completed"])

PREFIX_YOUTUBE_URL = "https://www.youtube.com/watch?v="

#검색된 영상들
with tab1:
    st.header("New Learning Videos")

    NUM_OF_VIDOES_PER_EACH_ROW = 2
    
    # New Learning에 표시할 영상
    for r in range(5): # 몇줄 출력할지
        cols = st.columns(NUM_OF_VIDOES_PER_EACH_ROW)
        for idx, item in enumerate(YoutubeVideo.youtube_list[r*NUM_OF_VIDOES_PER_EACH_ROW:r*NUM_OF_VIDOES_PER_EACH_ROW+NUM_OF_VIDOES_PER_EACH_ROW]):
            with cols[idx]:
                st.video(item.url) # 영상 띄우기

                extract_concepts(item.url)

                st.write(f"**{item.name}**")
                st.write(item.desc)

#이해 못한 영상과 개념
with tab2:
    st.header("Uncomprehended Videos")

    for video in YoutubeVideo.youtube_list: #현재는 유튜브 리스트지만 추후 시청한 영상 리스트로 변경
        if video.segment is not None:
            video_column, info_column = st.columns([2, 3])
            
            with video_column:
                st.video(video.url)  # Display the video
            
            with info_column:
                st.write(f"**{video.name}**")
                st.write(f"Segment: {video.segment}")

#이해한 개념
with tab3:
    st.header("Completed Videos")

    for video in YoutubeVideo.youtube_list: #현재는 유튜브 리스트지만 추후 시청한 영상 리스트로 변경
        if video.segment is not None:
            st.subheader(video.segment)

with open('style.css', 'rt', encoding='UTF8') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True )
