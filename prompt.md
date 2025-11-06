### **Project Goal:**

Build an interactive command-line tool in Python that scrapes all comments and replies from a specified YouTube channel. The tool must accept a full YouTube channel URL, display live processing status, and be able to resume from where it left off if interrupted. All extracted data will be saved into two separate, channel-specific JSON files in an `output/` directory.

### **Core Functional Requirements:**

1.  **Input:** The script must prompt the user to enter a full YouTube channel URL (e.g., `https://www.youtube.com/channel/UCBR8-60-B28hp2BmDPdntcQ`). The script will be responsible for parsing this URL to extract the `CHANNEL_ID`.
2.  **Video Retrieval:** It must find _all_ video IDs from the channel's "uploads" playlist.
3.  **Data Extraction (Two-File System):** The script must fetch and separate top-level comments from replies.
    - **Top-Level Comments:** For each video, retrieve all top-level comments.
    - **Sub-Comments (Replies):** For each top-level comment that has replies, retrieve all of its sub-comments.
4.  **Output:** All data must be saved in a folder named `output/`. For each channel processed, two JSON files must be created, named using the channel ID:
    - `output/[CHANNEL_ID]_comments.json`
    - `output/[CHANNEL_ID]_sub_comments.json`

### **Key Technical Requirements & Constraints:**

1.  **Use YouTube Data API v3:** The script **must** use the `google-api-python-client` library. Do not use direct web scraping.
2.  **API Key:** The script will require a valid YouTube Data API Key to be provided as a constant.
3.  **Interactive Terminal:** The script must show live progress. Use a library like `tqdm` to display a progress bar for video processing (e.g., `Processing video 75 of 320`).
4.  **Error Handling:** The script must gracefully handle API errors, especially:
    - `commentsDisabled`: If a video's comments are disabled, log this and continue.
    - `quotaExceeded`: If the API quota is hit, stop the script gracefully, ensuring all progress up to that point is saved.
5.  **Resumability (Critical):** If the script is stopped and re-run on the same channel, it **must** automatically detect where it left off and resume.
    - **Logic:** Before starting, the script must read the existing `[CHANNEL_ID]_comments.json` file.
    - It will create a `set` of all `videoLink`s or `videoId`s that are already in that file.
    - When fetching the list of all videos from the channel, it will skip any video that is already in this "processed" set.

### **Output Data Structures (Must Match Exactly)**

**1. `output/[CHANNEL_ID]_comments.json`**
This file will be a single JSON list containing objects for each top-level comment:

```json
[
  {
    "comment": "This is a great top-level comment!",
    "videoTitle": "The Title of Video 1",
    "videoLink": "https://www.youtube.com/watch?v=video_id_1",
    "datePostComment": "2025-11-04T10:30:01Z",
    "likesCount": 125
  },
  {
    "comment": "Another comment on a different video.",
    "videoTitle": "The Title of Video 2",
    "videoLink": "https://www.youtube.com/watch?v=video_id_2",
    "datePostComment": "2025-11-03T18:00:00Z",
    "likesCount": 10
  }
]
```

**2. `output/[CHANNEL_ID]_sub_comments.json`**
This file will be a single JSON list containing objects for each sub-comment (reply):

```json
[
  {
    "subComment": "This is a reply to the first comment.",
    "parentCommentId": "parent_comment_id_1",
    "videoTitle": "The Title of Video 1",
    "videoLinkId": "video_id_1",
    "datePostSubComment": "2025-11-04T11:00:00Z",
    "likeCount": 5
  },
  {
    "subComment": "Another reply.",
    "parentCommentId": "parent_comment_id_1",
    "videoTitle": "The Title of Video 1",
    "videoLinkId": "video_id_1",
    "datePostSubComment": "2025-11-04T12:00:00Z",
    "likeCount": 0
  }
]
```

### **Suggested Implementation Plan:**

1.  **Phase 1: Setup**

    - Import `googleapiclient.discovery`, `json`, `os`, `urllib.parse` (to parse the URL), and `tqdm`.
    - Define `API_KEY`.
    - Create `output/` directory: `os.makedirs("output", exist_ok=True)`.
    - Build the `youtube` service object.

2.  **Phase 2: Input & Resumption**

    - Prompt user for `channel_url`.
    - Create a function `get_channel_id_from_url(url)` to parse the URL and extract the `CHANNEL_ID`.
    - Define file paths: `comments_file = f"output/{channel_id}_comments.json"` and `sub_comments_file = f"output/{channel_id}_sub_comments.json"`.
    - Create a function `load_state(comments_file)`:
      - This function reads `comments_file` (if it exists) and returns two items:
        1.  A `set` of processed `videoLink`s to use for skipping.
        2.  The existing list of comments to which new comments will be appended.
    - Load the state: `processed_videos_set, master_comments_list = load_state(comments_file)`.
    - Load the existing sub-comments: `master_sub_comments_list = ...`

3.  **Phase 3: Get All Video IDs**

    - Create functions to get the `uploads_playlist_id` from the `channel_id`.
    - Create a function `get_all_video_ids_and_titles(youtube, playlist_id)` that paginates through all videos and returns a list of dictionaries: `[{"id": "...", "title": "..."}, ...]`.

4.  **Phase 4: Main Processing Loop**

    - Filter the full video list: `videos_to_process = [v for v in all_videos if f"https://www.youtube.com/watch?v={v['id']}" not in processed_videos_set]`.
    - **Start the interactive loop:** `for video in tqdm(videos_to_process, desc="Processing videos")`:
      - `video_id = video['id']`
      - `video_title = video['title']`
      - `video_link = f"https://www.youtube.com/watch?v={video_id}"`
      - Create lists for this video's data: `new_comments = []`, `new_sub_comments = []`.
      - **Try/Except Block:**
        - Call `youtube.commentThreads().list()` for `video_id` (paginating through all pages).
        - For each `comment_thread`:
          - Extract the top-level comment snippet.
          - Format it into the required `comment` object and add to `new_comments`.
          - `parent_comment_id = comment_thread['id']`
          - Check if it has replies. If so, call `youtube.comments().list(parentId=parent_comment_id)` (paginating through all replies).
          - For each `reply`:
            - Format it into the required `subComment` object and add to `new_sub_comments`.
      - **After each video is finished:**
        - `master_comments_list.extend(new_comments)`
        - `master_sub_comments_list.extend(new_sub_comments)`
        - **Atomically save progress:** Open `comments_file` and `json.dump(master_comments_list)`.
        - **Atomically save progress:** Open `sub_comments_file` and `json.dump(master_sub_comments_list)`.
    - Print "Processing complete\!"
