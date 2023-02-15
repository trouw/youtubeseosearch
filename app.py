import pinecone
import logging
import streamlit as st
from sentence_transformers import SentenceTransformer
from tqdm.auto import tqdm 

index_id = "seo-youtube-search"
pinecone_api = st.secrets["PINECONE_API"]

@st.cache_resource
def init_pinecone():
    pinecone.init(
    api_key=pinecone_api, 
    environment = "us-east1-gcp"
    )
    return pinecone.Index(index_id)

@st.cache_resource
def init_sbert():
    return SentenceTransformer('multi-qa-mpnet-base-dot-v1')

def make_query(query, model, top_k=10, include_values=True, include_metadata=True, filter=None):
    xq = model.encode([query]).tolist()
    logging.info(f"Query:{query}")
    attempt = 0 
    while attempt < 3: 
        try: 
            xc = st.session_state.index.query(
                xq, 
                top_k=top_k,
                include_values=include_values,
                include_metadata=include_metadata,
                filter=filter
            )
            matches = xc['matches']
            break
        except:
            pinecone.init(api_key=pinecone_api, environment = "us-east1-gcp")
            st.session_state.index = pinecone.Index(index_id)
            attempt += 1
            matches = []
    if len(matches) == 0:
        logging.error("Query Failed")
    return matches

def card(thumbnail: str, title: str, urls: list, contexts: list, starts: list, ends: list):
    meta = [(e,s,u,c) for e,s,u,c in zip(ends, starts, urls, contexts)]
    meta.sort(reverse=False)
    text_content = []
    current_start = 0
    current_end = 0
    for end, start, url, contexts in meta:
        time = start / 60 
        mins = f"0{int(time)}"[-2:]
        secs = f"0{int(round((time - int(mins))*60, 0))}"[-2:]
        timestamp = f"{mins}:{secs}"
        if start < current_end and start > current_start:
            text_content[-1][0] = text_content[-1][0].split(contexts[:10])[0]
            text_content.append([f"[{timestamp}] {contexts.capitalize()}", url])
        else: 
            text_content.append(["xLINEBREAKx", ""])
            text_content.append([f"[{timestamp}] {contexts}", url])
        current_start = start
        current_end = end
    html_text = ""
    for text, url in text_content:
        if text == "xLINEBREAKx":
            html_text += "<br>"
        else: 
            html_text += f"<small><a href={url}>{text.strip()}... </a></small>"
    html = f"""
    <div class="container-fluid">
        <table class"table-fluid">
            <tr>
                <th><a href={urls[0]}><img src={thumbnail} class="img-fluid" style="width: 192px; height: 106px"></a></th>
                <th><h2>{title}</h2>
            </tr>
        </table>
        <div>
            <p>{html_text}</p>
        </div>
    </div>
    <br><br>
    """
    return st.markdown(html, unsafe_allow_html=True)

st.session_state.index = init_pinecone()
model = init_sbert()

st.title('A Better YouTube Search for SEOs')

container = st.container()
container.write("There is an abundance of excellent resources for SEO professionals on YouTube, yet finding the information you need can be a challenge. Despite the wealth of informative videos, webinars, and conference replays offered by publishers like Google Search Console, Moz, Ahrefs, and SEMrush, sifting through hours of content to find the answer to a specific query can be time-consuming and inefficient.")
container.write("Use this tool to efficiently find answers to complex SEO questions by semantically searching through an index of 1550 videos.")
container.write("Created by [Tyler Rouwhorst](https://www.linkedin.com/in/tyler-rouwhorst/)")

st.info("Disclaimer: The index was built on Feb 8th, 2023 so any video published after this date by the included publishers will not be included. Additionally, searchers should be aware of the published date of a video result to ensure information on a specific topic is up to date.")

query = st.text_input('Search!', '')

with st.expander("Advanced Options"):
    channel_options = st.multiselect(
        'Select Channels to Search',
        ['GSC', 'SEMrush', 'Ahrefs', 'MOZ'],
        ['GSC', 'SEMrush', 'Ahrefs', 'MOZ']
    )
    year_options = st.multiselect(
        'Select Year of Publication to Search',
        ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023'],
        ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023']
    )

if query != '':
    matches = make_query(
        query, model, top_k=10,
        filter={
            'channel': {'$in': channel_options},
            'publish': {'$in': year_options}
        }
    )

    results = {}
    order =[]

    for context in matches: 
        video_id = context['metadata']['url'].split('/')[-1]
        subtract_vid_id = 'watch?v='
        video_id = video_id.replace(subtract_vid_id,'')
        if video_id not in results: 
            results[video_id] = {
                'title': context['metadata']['title'],
                'urls': [f"{context['metadata']['url']}&t={int(context['metadata']['start'])}"],
                'contexts': [context['metadata']['text']],
                'starts': [int(context['metadata']['start'])],
                'ends': [int(context['metadata']['end'])]
            }
            order.append(video_id)
        else: 
            results[video_id]['urls'].append(
                f"{context['metadata']['url']}&t={int(context['metadata']['start'])}"
                )
            results[video_id]['contexts'].append(
                context['metadata']['text']
                )
            results[video_id]['starts'].append(int(context['metadata']['start']))
            results[video_id]['ends'].append(int(context['metadata']['end']))
    for video_id in order:
        card(
            thumbnail=f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            title=results[video_id]['title'],
            urls=results[video_id]['urls'],
            contexts=results[video_id]['contexts'],
            starts=results[video_id]['starts'],
            ends=results[video_id]['ends']
        )


