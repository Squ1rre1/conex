import streamlit as st
import googleapiclient.discovery
import streamlit.components.v1 as components
import utils

class YoutubeVideo:
    youtube_list = list()
    def __init__(self,name,url,desc):
        self.name=name
        self.url=url
        self.desc=desc
        self.watch=None
        self.segment=None
        self.youtube_list.append(self)
    
    @classmethod
    def list_reset(cls):
        cls.youtube_list.clear()
        
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
    
    # 유튜브 리스트 객체 생성
    for item in response['items']:
        name = item['snippet']['title']
        url = PREFIX_YOUTUBE_URL + item['id']['videoId']
        desc = utils.truncate_text ( item['snippet']['description'] )
        video_init = YoutubeVideo(name=name,url=url,desc=desc)
    
    #test
    #print(YoutubeVideo.youtube_list[0].url)
    return response, YoutubeVideo.youtube_list


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
    new_videos, video_list = search_youtubes(user_input) # 검색한 영상 받아온 리스트

# 페이지 1, 2, 3 
tab1, tab2, tab3 = st.tabs(["New Learning", "Uncomprehended", "Completed"])

PREFIX_YOUTUBE_URL = "https://www.youtube.com/watch?v="

with tab1:
    st.header("New Learning Videos")

    NUM_OF_VIDOES_PER_EACH_ROW = 2
    
    # New Learning에 표시할 영상
    for r in range(5): # 몇줄 출력할지
        cols = st.columns(NUM_OF_VIDOES_PER_EACH_ROW)
        for idx, item in enumerate(new_videos['items'][r*NUM_OF_VIDOES_PER_EACH_ROW:r*NUM_OF_VIDOES_PER_EACH_ROW+NUM_OF_VIDOES_PER_EACH_ROW]):
            vidId = item['id']['videoId']
            title = item['snippet']['title']
            desc = utils.truncate_text ( item['snippet']['description'] )
            with cols[idx]:
                st.video(PREFIX_YOUTUBE_URL + vidId) # 영상 띄우기

                extract_concepts(vidId)

                st.write(f"**{title}**")
                st.write(desc)
                

with open('style.css', 'rt', encoding='UTF8') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True )
    