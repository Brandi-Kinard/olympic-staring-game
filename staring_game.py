import streamlit as st
import cv2
import dlib
import numpy as np
import time
import sqlite3
import pandas as pd
import base64
import psycopg2
import os
import hashlib
import streamlit.components.v1 as components
import socketio

# create a Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = socketio.ASGIApp(sio)

# define a socket connection event
@sio.event
def connect(sid, environ):
    print('Client connected:', sid)

@sio.event
def disconnect(sid):
    print('Client disconnected:', sid)

@sio.on('frame')
async def handle_frame(sid, data):
    try:
        file_bytes = np.asarray(bytearray(data), dtype=np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        blink_detected, game_time = process_frame(frame)  # Ensure this function is robust
        username = 'extracted_username_here'  # Properly fetch the username

        if blink_detected:
            update_leaderboard(username, game_time)
            leaderboard = get_leaderboard()
            await sio.emit('leaderboard_update', {'leaderboard': leaderboard}, room=sid)
    except Exception as e:
        await sio.emit('error', {'message': str(e)}, room=sid)
        print(f"Error handling frame data: {str(e)}")


# Initialize necessary components
detector = dlib.get_frontal_face_detector()

def file_hash(filename):
    with open(filename, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(4096):
            file_hash.update(chunk)
    return file_hash.hexdigest()

def log_file_details(path):
    if os.path.exists(path):
        file_size = os.path.getsize(path)
        file_md5 = file_hash(path)
        print(f"File exists: {path}, Size: {file_size}, MD5: {file_md5}")
    else:
        print(f"File not found: {path}")

# Log details about the shape predictor file
log_file_details('shape_predictor_68_face_landmarks.dat')

# Then attempt to load it with dlib
try:
    predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')
except Exception as e:
    print(f"Failed to load shape predictor due to: {e}")

# Set up the database connection
try:
    DATABASE_URL = os.environ['DATABASE_URL']
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard (
            username TEXT, 
            team TEXT, 
            score REAL
        );
    ''')
    conn.commit()
except Exception as e:
    st.error(f"Failed to connect to the database or execute a query: {str(e)}")


def eye_aspect_ratio(eye_points, facial_landmarks):
    p2_p6 = np.linalg.norm([facial_landmarks.part(eye_points[1]).x - facial_landmarks.part(eye_points[5]).x,
                            facial_landmarks.part(eye_points[1]).y - facial_landmarks.part(eye_points[5]).y])
    p3_p5 = np.linalg.norm([facial_landmarks.part(eye_points[2]).x - facial_landmarks.part(eye_points[4]).x,
                            facial_landmarks.part(eye_points[2]).y - facial_landmarks.part(eye_points[4]).y])
    p1_p4 = np.linalg.norm([facial_landmarks.part(eye_points[0]).x - facial_landmarks.part(eye_points[3]).x,
                            facial_landmarks.part(eye_points[0]).y - facial_landmarks.part(eye_points[3]).y])
    return (p2_p6 + p3_p5) / (2.0 * p1_p4)

def make_red(text):
  """Returns HTML with the provided text wrapped in a red span"""
  return f'<span class="red-text">{text}</span>'


def main():
    # Olympic rings image centered
    col1, col2, col3, col4, col5 = st.columns([0.5, 0.5, 1, 0.5, 0.5])

    # Using the middle column to center the image with adjusted width
    with col3:
        st.image('https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExYXp3a296OTcxMTl2bmxzdzdlYWhyNmF1M3Q5cWptd3VtcWlwcmE4NSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/K7LqsCtmYyebqrhOKr/giphy.gif', width=100, use_column_width=True)

    # Display the title "EyeQ" and "Beta"
    st.markdown(f"""<div style='text-align: center;'>
                        <span style='font-size: 96px; font-weight: bold;'>EyeQ</span>
                        <span style='font-size: 24px; color: #2E9BF5; vertical-align: super; font-weight: bold;'> Beta</span>
                    </div>""", unsafe_allow_html=True)

    # Display the description text centered below the title
    st.markdown("""
        <div style='text-align: center; font-size: 24px;'>
            Test your focus, claim your fame in the  
            <span style='color: #2E9BF5; font-weight: bold;'>Olympic staring contest</span>. 
            Can you outstare the world?
        </div>
    """, unsafe_allow_html=True)

    # Extra lines of space
    st.text(" ")
    st.text(" ")

    # Follow me links
    def get_image_base64(path):
        """Load and convert images to base64."""
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()

    # Load images and convert to base64
    gith_image_base64 = get_image_base64('gith.png')
    linkedi_image_base64 = get_image_base64('linkedi.png')
    portfolio_image_base64 = get_image_base64('portfolio.png')

    # HTML template for displaying the images with links
    html_template = """
    <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 20px;">
        <span style='margin-right: 10px; font-size: 20px; vertical-align: middle;'>Follow:</span>
        <a href="{0}" target="_blank"><img src="data:image/png;base64,{1}" style="width:24px; height:24px; margin-right: 5px;"></a>
        <a href="{2}" target="_blank"><img src="data:image/png;base64,{3}" style="width:24px; height:24px; margin-right: 5px;"></a>
        <a href="{4}" target="_blank"><img src="data:image/png;base64,{5}" style="width:24px; height:24px;"></a>
    </div>
    """.format(
        "https://github.com/Brandi-Kinard", gith_image_base64,
        "https://www.linkedin.com/in/brandi-kinard/", linkedi_image_base64,
        "https://brandikinard.com/", portfolio_image_base64
    )

    # Use markdown to display the HTML content
    st.markdown(html_template, unsafe_allow_html=True)

    # Extra lines of space
    st.text(" ")
    st.text(" ")

    with st.sidebar:

        st.markdown(f"""<div style='text-align: left;'>
                                <span style='font-size: 20px; font-weight: bold;'>Welcome to EyeQ!</span>
                            </div>""", unsafe_allow_html=True)
        st.markdown("""
            Challenge your skills in the Olympic-style staring contest and see how long you can last without blinking.
        """, unsafe_allow_html=True)


        st.markdown("---")


        # How to Play Section
        st.header("How to Play")
        st.markdown("Follow these simple steps:")

        st.markdown("1. **Enter Your Username and Select Your Team**")
        st.image('step1.png')

        st.markdown("2. **Press 'Start Game' and Stare Into the Camera**")
        st.image('step2.png', caption="Try not to blink and focus as long as you can.")

        st.markdown("3. **End Game on Blink**")
        st.image('step3.png', caption="Your score displays once you blink.")

        st.markdown("4. **See Your Ranking and Play Again**")
        st.image('step4.png', caption="You can start the game as many times as you want.")

        st.markdown("---")

        # Tips Section
        st.subheader("Tips for the Best Experience")
        st.markdown("""
            - **Camera Access:** Make sure your camera is enabled.
            - **Lighting:** Play in a well-lit area to improve camera visibility.
            - **Position:** Face directly towards your camera.
            - **Clear Face:** Avoid wearing glasses or masks that might obstruct your face.
        """, unsafe_allow_html=True)

        # Extra lines of space
        st.text(" ")
        st.text(" ")

        st.markdown("[What's the purpose of this app?](https://github.com/Brandi-Kinard/olympic-staring-game)")

        st.markdown("---")

        col1, col2, col3 = st.columns([1, 0.5, 0.5
                                       ])
        # Using the middle column to center the image with adjusted width
        with col1:
            st.image('eyeqlogohorizontalbw.png', width=100, use_column_width=True)
        st.text(" ")
        st.caption("Made by [Brandi Kinard](https://www.linkedin.com/in/brandi-kinard/)")

        # Extra lines of space
        st.text(" ")
        st.text(" ")

        st.caption("This app is a personal project for entertainment purposes only and is not affiliated with the "
                   "Olympic Games. It uses your webcam to simulate a staring contest but does not store or transmit any "
                   "personal or biometric data.")

    team_options = ["Select a team"] + [
        "🇺🇸 USA",
        "🇦🇫 Afghanistan", "🇦🇱 Albania", "🇩🇿 Algeria", "🇦🇩 Andorra", "🇦🇴 Angola",
        "🇦🇬 Antigua and Barbuda", "🇦🇷 Argentina", "🇦🇲 Armenia", "🇦🇺 Australia", "🇦🇹 Austria",
        "🇦🇿 Azerbaijan", "🇧🇸 Bahamas", "🇧🇭 Bahrain", "🇧🇩 Bangladesh", "🇧🇧 Barbados",
        "🇧🇾 Belarus", "🇧🇪 Belgium", "🇧🇿 Belize", "🇧🇯 Benin", "🇧🇹 Bhutan",
        "🇧🇴 Bolivia", "🇧🇦 Bosnia and Herzegovina", "🇧🇼 Botswana", "🇧🇷 Brazil", "🇧🇳 Brunei",
        "🇧🇬 Bulgaria", "🇧🇫 Burkina Faso", "🇧🇮 Burundi", "🇰🇭 Cambodia", "🇨🇲 Cameroon",
        "🇨🇦 Canada", "🇨🇻 Cape Verde", "🇨🇫 Central African Republic", "🇹🇩 Chad", "🇨🇱 Chile",
        "🇨🇳 China", "🇨🇴 Colombia", "🇰🇲 Comoros", "🇨🇬 Congo - Brazzaville", "🇨🇩 Congo - Kinshasa",
        "🇨🇷 Costa Rica", "🇭🇷 Croatia", "🇨🇺 Cuba", "🇨🇾 Cyprus", "🇨🇿 Czechia",
        "🇩🇰 Denmark", "🇩🇯 Djibouti", "🇩🇲 Dominica", "🇩🇴 Dominican Republic", "🇪🇨 Ecuador",
        "🇪🇬 Egypt", "🇸🇻 El Salvador", "🇬🇶 Equatorial Guinea", "🇪🇷 Eritrea", "🇪🇪 Estonia",
        "🇸🇿 Eswatini", "🇪🇹 Ethiopia", "🇫🇯 Fiji", "🇫🇮 Finland", "🇫🇷 France",
        "🇬🇦 Gabon", "🇬🇲 Gambia", "🇬🇪 Georgia", "🇩🇪 Germany", "🇬🇭 Ghana",
        "🇬🇷 Greece", "🇬🇩 Grenada", "🇬🇹 Guatemala", "🇬🇳 Guinea", "🇬🇼 Guinea-Bissau",
        "🇬🇾 Guyana", "🇭🇹 Haiti", "🇭🇳 Honduras", "🇭🇺 Hungary", "🇮🇸 Iceland",
        "🇮🇳 India", "🇮🇩 Indonesia", "🇮🇷 Iran", "🇮🇶 Iraq", "🇮🇪 Ireland",
        "🇮🇱 Israel", "🇮🇹 Italy", "🇯🇲 Jamaica", "🇯🇵 Japan", "🇯🇴 Jordan",
        "🇰🇿 Kazakhstan", "🇰🇪 Kenya", "🇰🇮 Kiribati", "🇰🇷 South Korea", "🇰🇼 Kuwait",
        "🇰🇬 Kyrgyzstan", "🇱🇦 Laos", "🇱🇻 Latvia", "🇱🇧 Lebanon", "🇱🇸 Lesotho",
        "🇱🇷 Liberia", "🇱🇾 Libya", "🇱🇮 Liechtenstein", "🇱🇹 Lithuania", "🇱🇺 Luxembourg",
        "🇲🇬 Madagascar", "🇲🇼 Malawi", "🇲🇾 Malaysia", "🇲🇻 Maldives", "🇲🇱 Mali",
        "🇲🇹 Malta", "🇲🇭 Marshall Islands", "🇲🇷 Mauritania", "🇲🇺 Mauritius", "🇲🇽 Mexico",
        "🇫🇲 Micronesia", "🇲🇩 Moldova", "🇲🇨 Monaco", "🇲🇳 Mongolia", "🇲🇪 Montenegro",
        "🇲🇦 Morocco", "🇲🇿 Mozambique", "🇲🇲 Myanmar (Burma)", "🇳🇦 Namibia", "🇳🇷 Nauru",
        "🇳🇵 Nepal", "🇳🇱 Netherlands", "🇳🇿 New Zealand", "🇳🇮 Nicaragua", "🇳🇪 Niger",
        "🇳🇬 Nigeria", "🇲🇰 North Macedonia", "🇳🇴 Norway", "🇴🇲 Oman", "🇵🇰 Pakistan",
        "🇵🇼 Palau", "🇵🇸 Palestine", "🇵🇦 Panama", "🇵🇬 Papua New Guinea", "🇵🇾 Paraguay",
        "🇵🇪 Peru", "🇵🇭 Philippines", "🇵🇱 Poland", "🇵🇹 Portugal", "🇶🇦 Qatar",
        "🇷🇴 Romania", "🇷🇺 Russia", "🇷🇼 Rwanda", "🇰🇳 Saint Kitts and Nevis", "🇱🇨 Saint Lucia",
        "🇻🇨 Saint Vincent and the Grenadines", "🇼🇸 Samoa", "🇸🇲 San Marino", "🇸🇹 São Tomé and Príncipe",
        "🇸🇦 Saudi Arabia",
        "🇸🇳 Senegal", "🇷🇸 Serbia", "🇸🇨 Seychelles", "🇸🇱 Sierra Leone", "🇸🇬 Singapore",
        "🇸🇰 Slovakia", "🇸🇮 Slovenia", "🇸🇧 Solomon Islands", "🇸🇴 Somalia", "🇿🇦 South Africa",
        "🇰🇷 South Korea", "🇸🇸 South Sudan", "🇪🇸 Spain", "🇱🇰 Sri Lanka", "🇸🇩 Sudan",
        "🇸🇷 Suriname", "🇸🇪 Sweden", "🇨🇭 Switzerland", "🇸🇾 Syria", "🇹🇼 Taiwan",
        "🇹🇯 Tajikistan", "🇹🇿 Tanzania", "🇹🇭 Thailand", "🇹🇱 Timor-Leste", "🇹🇬 Togo",
        "🇹🇴 Tonga", "🇹🇹 Trinidad and Tobago", "🇹🇳 Tunisia", "🇹🇷 Turkey", "🇹🇲 Turkmenistan",
        "🇹🇻 Tuvalu", "🇺🇬 Uganda", "🇺🇦 Ukraine", "🇦🇪 United Arab Emirates", "🇬🇧 United Kingdom",
        "🇺🇾 Uruguay", "🇺🇿 Uzbekistan", "🇻🇺 Vanuatu", "🇻🇪 Venezuela", "🇻🇳 Vietnam",
        "🇾🇪 Yemen", "🇿🇲 Zambia", "🇿🇼 Zimbabwe"
    ]

    if 'username' not in st.session_state or 'team' not in st.session_state:
        user_input = st.text_input("Username", value='', max_chars=24,
                                   placeholder="Create a username",
                                   help="Choose a unique username to identify yourself in the competition. Max 24 characters.")
        selected_team = st.selectbox("Team", team_options, index=0, help="Choose a team to compete for. Scroll to see all options or search by name.")

        if user_input and selected_team != "Select a team":
            if username_exists(user_input):
                st.error("This username is already taken. Please choose another.")
            else:
                st.session_state.username = user_input
                st.session_state.team = selected_team
                if st.button('Start Game'):
                    countdown(3)
                    start_game(st.session_state.username, st.session_state.team)
        else:
            st.button('Start Game', disabled=True)
    else:
        st.write(f"{st.session_state.username}, competing for Team {st.session_state.team}")
        if st.button('Start Game'):
            countdown(3)
            start_game(st.session_state.username, st.session_state.team)


def username_exists(username):
    c.execute("SELECT 1 FROM leaderboard WHERE username = %s", (username,))
    return c.fetchone() is not None

def countdown(t):
    countdown_container = st.empty()
    for i in range(t, 0, -1):
        countdown_container.write(f'Starting in {i}...')
        time.sleep(1)
    countdown_container.write('Go!')
    time.sleep(1)
    countdown_container.empty()

def start_game(user_name, team):
    if 'leaderboard' not in st.session_state:
        st.session_state.leaderboard = []

    # Embed custom HTML to access the webcam
    webcam_html = """
    <html>
    <body>
    <!-- Stream video from webcam -->
    <video id="video" width="640" height="480" autoplay></autoplay>
    <div id="leaderboard"></div> <!-- Container for the leaderboard -->
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script>
    var video = document.querySelector("#video");
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
    
    function sendFrame() {
        video.requestVideoFrameCallback(() => {
            var canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            var ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(blob => {
                socket.emit('frame', blob);
            });
            sendFrame(); // Recursively send frames
        });
    }
    
    socket.on('blink_detected', function(data) {
        document.body.innerHTML += `<div style="position: fixed; top: 10px; left: 10px;">🎈 Blink detected at ${data.game_time} seconds! 🎈</div>`;
    });
    
    socket.on('leaderboard_update', function(data) {
        updateLeaderboardUI(data.leaderboard);
    });
    
    function updateLeaderboardUI(leaderboard) {
        var leaderboardHTML = '<ul>';
        for (var i = 0; i < leaderboard.length; i++) {
            leaderboardHTML += `<li>${leaderboard[i].username}: ${leaderboard[i].score} seconds</li>`;
        }
        leaderboardHTML += '</ul>';
        document.getElementById('leaderboard').innerHTML = leaderboardHTML;
    }

    if (navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(function (stream) {
                video.srcObject = stream;
                sendFrame(); // Start sending frames when the stream is ready
            })
            .catch(function (error) {
                console.log("Something went wrong!", error);
            });
    }
    </script>
    </body>
    </html>
    """

    components.html(webcam_html, height=480)

    if st.button('Analyze'):
        # Placeholder for sending video frames to server for analysis
        st.write('Analyzing...')  # Implement this part based on your application's needs

def update_leaderboard(user_name, team, game_time):
    c.execute('INSERT INTO leaderboard (username, team, score) VALUES (%s, %s, %s)', (user_name, team, game_time))
    conn.commit()
    c.execute('SELECT username, team, score FROM leaderboard ORDER BY score DESC')
    records = c.fetchall()
    display_leaderboard(records)

def display_leaderboard(records):
    st.write('### Leaderboard')
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * (len(records) - 3)
    df = pd.DataFrame(records, columns=['Username', 'Team', 'Time'])
    df['Rank'] = [f"{idx} {medals[idx-1]}" for idx in range(1, len(records)+1)]
    df.set_index('Rank', inplace=True)
    st.table(df)

def show_toast_messages(game_time, user_name):
    st.toast('Hip!')
    time.sleep(.5)
    st.toast('Hip!')
    time.sleep(.5)
    c.execute('SELECT username, team, score FROM leaderboard ORDER BY score DESC')
    leaderboard = c.fetchall()
    rank = next((idx for idx, rec in enumerate(leaderboard, 1) if rec[0] == user_name), len(leaderboard))
    medal_icon = "🎉" if rank > 3 else ["🥇", "🥈", "🥉"][rank-1]
    st.toast(f'Hooray!', icon=medal_icon)
    time.sleep(.5)
    st.toast(f'Blink detected at {game_time:.2f} seconds! {user_name} ranked #{rank} {medal_icon}')

if __name__ == "__main__":
    main()
