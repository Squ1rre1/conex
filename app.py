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
import os
import pickle
from pyvis.network import Network
from datetime import datetime, timedelta

# 옵션 기본값
NUM_OF_VIDEOS = 10
TIME_DIVISION = 600
NUM_OF_WORDS = 5
OUT_FILENAME = "./data/watchedVideo_concepts.csv"

# 유튜브 검색시 유튜브 리스트 저장
class YoutubeVideo:
    youtube_list = list()
    def __init__(self,name,url,desc,duration):
        self.name=name
        self.url=url
        self.desc=desc
        self.duration=duration
        self.watch=False
        self.segment=None
        self.youtube_list.append(self)

# 본 영상을 저장하는 리스트, 저장 이슈로 인해 파일입출력
with open("./data/watchedVideo.pkl", "rb") as file:
    watchedVideo = pickle.load(file)

with open("./data/new_learning_list.pkl", "rb") as file:
    new_learning_list = pickle.load(file)

with open("./data/selected_video.pkl", "rb") as file:
    selected_video = pickle.load(file)

class Script_Exctractor:
    def __init__(self,vid,setTime):
        self.vid = vid
        self.scriptData:list = []
        self.setTime = setTime
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

        for i in range(len(self.scriptData)):
            text = self.scriptData[i].replace(u'\xa0', u' ').replace(u'\n',u' ').replace(u'  ',u' ')
            self.scriptData[i] = text

    def CallWikifier(self, text, lang="en", threshold=0.8, numberOfKCs=10):
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
            print(f"{number} segemnt")
            results.append(self.CallWikifier(text=text, numberOfKCs=NUM_OF_WORDS))
            number += 1

        wiki_data = pd.DataFrame()
        seg_no = 1

        for seg_item in results:
            # seg_index = range(0,len(seg_item))
            # seg_df = pd.DataFrame(seg_item,index = seg_index)
            seg_df = pd.DataFrame(seg_item)
            seg_df['seg_no'] = seg_no
            seg_df['understand']=0
            wiki_data = pd.concat([wiki_data,seg_df])
            seg_no = seg_no + 1
        wiki_data.index = range(len(wiki_data))
        return wiki_data

YOUTUBE_API_KEY = "AIzaSyCt74iOovLdzJMGCfsCAW4nAssQB8LJWo0"

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
    st.write("Swimming in the vast sea of online lectures")
    st.markdown("## About")
    st.markdown("**CONEX** aids in the continuous exploration of specialized concept(a.k.a knowledge) that is yet unfamiliar, derived from a vast amount of online lectures.")
    st.markdown("## Features")
    st.markdown(""" 
                    - allows learners to easily and quickly access new concepts related to the specialized knowledge within lectures
                    - assists in understanding their definitions on Wikipedia
                    - provides pre-filtered lectures to identify concepts that are not learned yet
                    - enables learners to catch those concepts in other lectures""")
    st.markdown("---")
    st.markdown("Options for Search")
    NUM_OF_VIDEOS = st.number_input("The number of recommended videos", value=NUM_OF_VIDEOS)
    TIME_DIVISION = st.number_input("The interval of segment (in seconds)", value=TIME_DIVISION)
    NUM_OF_WORDS = st.number_input("The number of concepts extracted per each segment", value=NUM_OF_WORDS)
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

def search_youtubes(query, video_count):
    VIDEO_COUNT=video_count # 유튜브에서 들고 올 영상 수
    PREFIX_YOUTUBE_URL = "https://www.youtube.com/watch?v="
    
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
        else:
            print("영상 길이 문제로 필터링됨")
    
    return YoutubeVideo.youtube_list

def make_csv():
    video_names = []
    concepts = []
    pageranks = []
    understands = []

    # Loop through each video in watchedVideo
    for video in watchedVideo:
        if video.segment is not None:
            # Loop through each segment and its concepts
            for seg_no, row in video.segment.iterrows():
                video_names.append(video.name)
                concepts.append(row['title'])
                pageranks.append(row['pageRank'])
                understands.append(row['understand'])

    # Create a DataFrame from the lists
    data = {
        'videoname': video_names,
        'concept': concepts,
        'pagerank': pageranks,
        'understand': understands
    }
    df = pd.DataFrame(data)

    # Save DataFrame to a CSV file
    df.to_csv(OUT_FILENAME, index=False)

# csv파일을 통해 그래프 시각화
def visualize_dynamic_network():
    got_net = Network(width="1200px", height="800px", bgcolor="#EEEEEF", font_color="white", notebook=True)

    # set the physics layout of the network
    got_net.barnes_hut()

    if os.path.exists(OUT_FILENAME): 
        got_data = pd.read_csv(OUT_FILENAME)

        videoname = got_data['videoname']
        concept = got_data['concept']
        pagerank = got_data['pagerank']
        understand = got_data['understand']
        
        got_net.show_buttons(filter_=['physics'])

        edge_data = zip(videoname,concept,pagerank,understand)

        for e in edge_data:
            vid = e[0]
            con = e[1]
            pag = e[2]
            und = e[3]

            node_color = "red" if und == 1 else "black"
            node_size = 50 + 1000 * pag #pagerank가 클수록 노드가 커지도록함
            
            got_net.add_node(vid, vid, title=vid,size=100)
            got_net.add_node(con, con, title=con, color=node_color, size=node_size)
            got_net.add_edge(vid, con, value=1)

        got_net.show("./data/gameofthrones.html")

        with open("./data/gameofthrones.html", "r") as f:
            graph_html = f.read()
        st.components.v1.html(graph_html,width=1200, height=800) 

# 개념 동그라미를 그리는 함수
def extract_concepts(selected_video):
    start_time = "2023-08-02 00:00:00"  # start time
    start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")

    if selected_video.segment is not None:
        # Loop through each segment and display concepts in circular and rectangular buttons
        for seg_no, segment_data in selected_video.segment.groupby('seg_no'):
            start_segment = start_datetime + timedelta(seconds=(seg_no - 1) * TIME_DIVISION)
            end_segment = start_datetime + timedelta(seconds=seg_no * TIME_DIVISION)

            st.markdown(f"<h5>(segment {seg_no}) {start_segment.strftime('%H:%M:%S')} - {end_segment.strftime('%H:%M:%S')}</h5>", unsafe_allow_html=True)

            cols = st.columns(len(segment_data))
            
            # Display concepts with buttons
            for index, row in segment_data.iterrows():
                title = row['title']
                understand = row['understand']

                # Button style based on understand column
                if understand == 0:
                    button_style = "black"
                else:
                    button_style = "red"

                with cols[index % len(segment_data)]:
                    # Button click event
                    if st.button(f":{button_style}[{title}]", key=f"{selected_video.name}_{seg_no}_{index}", help=f"{seg_no}_{index}"):
                        # Toggle 'understand' value when the button is clicked
                        understand = selected_video.segment.at[index, 'understand']

                        if understand == 0:
                            clicked_word_url = row['url']
                            # Update 'understand' to 1 for all rows with the same URL
                            selected_video.segment.loc[selected_video.segment['url'] == clicked_word_url, 'understand'] = 1
                        else:
                            clicked_word_url = row['url']
                            # Update 'understand' to 1 for all rows with the same URL
                            selected_video.segment.loc[selected_video.segment['url'] == clicked_word_url, 'understand'] = 0
                        
                        for idx,video in enumerate(watchedVideo):
                            if(video.name==selected_video.name):
                                watchedVideo[idx]=selected_video
                                with open("./data/watchedVideo.pkl", "wb") as file:
                                    pickle.dump(watchedVideo, file)
                                with open("./data/selected_video.pkl", "wb") as file:
                                    pickle.dump(selected_video, file)
                        
                        make_csv() #csv파일로 df저장
    else:
        st.write("No segment information available for the selected video.")

user_input = get_text()
search_button = st.button("Search")  # 버튼 추가

if search_button and user_input:
    new_learning_list = search_youtubes(user_input, NUM_OF_VIDEOS) # 검색한 영상 받아온 리스트
    # 위키화 및 랭크
    for index, video in enumerate(new_learning_list):
        try:
            Scripts = Script_Exctractor(video.url, TIME_DIVISION)
            video.segment = Scripts.UrltoWiki()
            # print(video.segment) # 각 영상당 만들어진 segment 출력
        except Exception as ex:
            # print(ex) # 에러문 출력
            print(f"{index}번째 영상 삭제")
            new_learning_list.pop(index)
    print(f"영상 개수: {len(new_learning_list)}")
    with open("./data/new_learning_list.pkl", "wb") as file:
        pickle.dump(new_learning_list, file)

tab1, tab2, tab3, tab4  = st.tabs(["New Learning", "History", "Concepts Network", "Watching"])

# 선택된 영상 불러오기, 저장 이슈로 파일 입출력
# selected_video = None
with open("./data/selected_video.pkl", "rb") as file:
    selected_video = pickle.load(file)

#검색된 영상들
with tab1:
    st.header("New Learning Videos")
    st.write("The new learning videos contain new concepts that you have not been learned")

    NUM_OF_VIDOES_PER_EACH_ROW = 2
    
    # New Learning에 표시할 영상
    for r in range(int(NUM_OF_VIDEOS/2)): # 몇줄 출력할지
        cols = st.columns(NUM_OF_VIDOES_PER_EACH_ROW)
        for idx, item in enumerate(new_learning_list[r*NUM_OF_VIDOES_PER_EACH_ROW:r*NUM_OF_VIDOES_PER_EACH_ROW+NUM_OF_VIDOES_PER_EACH_ROW]):
            with cols[idx]:
                if st.button(f"Watch: {item.name}"):  
                    # 이미 시청한 영상을 클릭하면 시청했던 영상 정보로 불러오기
                    # 시청안했다면 시청 리스트에 포함 시키기
                    st.success('When you navigate to the "Watching" tab, you can watch videos.', icon="😃")
                    count=0
                    for video in watchedVideo:
                        if (video.name==item.name):
                            count=1
                            selected_video = video  # 클릭한 영상 정보 저장
                            with open("./data/selected_video.pkl", "wb") as file:
                                pickle.dump(selected_video, file)
                    if(count==0):
                        watchedVideo.append(item) # 클릭 영상 리스트에 저장
                        with open("./data/watchedVideo.pkl", "wb") as file:
                            pickle.dump(watchedVideo, file)
                        selected_video = item  # 클릭한 영상 정보 저장
                        with open("./data/selected_video.pkl", "wb") as file:
                            pickle.dump(selected_video, file)
                
                st.video(item.url) # 영상 표시
                #extract_concepts(item.url)

                st.write(f"**{item.name}**")
                st.write(item.desc)

#클릭한 영상을 크게 보여주는 탭 # selected_video 변수가 tab2,3에서 사용돼서 tab4 먼저 적음
with tab4:
    st.header("Watching a Video")
    st.write("This tab is to watch the selected lecture video. Please click on the concepts in the segment at the bottom if you understand them in the lecture. Are there any concepts you do not understand? CONEX recommends the sets of another lectures to help you understand the concepts you have not learned in the New Learning Video tab.")

    if selected_video:
        st.subheader(selected_video.name)
        st.video(selected_video.url)
        st.write("Red words: you understand the concept, Black words: you don't understand it yet")
        if selected_video.segment is not None:
            extract_concepts(selected_video)
    else:
        st.write("Click on a video in 'New Learning Videos' tab to watch it here.")

#이해 못한 영상과 개념
with tab2:
    st.header("History of Videos You Watched")
    st.write("This tab shows the history of lecture videos you watched.")

    for video in watchedVideo: 
        if video.segment['understand'].all() == 1:
            continue
        if st.button(f"Re Watch: {video.name}"):  
            selected_video = video  # 클릭한 영상 정보 저장
            with open("./data/selected_video.pkl", "wb") as file:
                pickle.dump(selected_video, file)
        if video.segment is not None:
            video_column, info_column = st.columns([2, 3])
            
            with video_column:
                st.video(video.url)  # Display the video
            
            with info_column:
                st.write(f"**{video.name}**")
                st.write(f"Each segment is ({TIME_DIVISION} seconds): \n")
                st.dataframe(video.segment)

#이해한 개념
with tab3:
    st.header("Visualization: The Network of Concepts You Have Learned")
    st.write("This tab visualizes the concepts encountered in the videos you've learned. Sky blue nodes represent the videos you've watched, while red nodes indicate the concepts you've understood. Black nodes represent concepts you haven't grasped yet. If different videos refer to the same concept, they will be connected as a single node.")
    visualize_dynamic_network()

with open('style.css', 'rt', encoding='UTF8') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True )