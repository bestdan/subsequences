const socket = io();
let myTurn = false;

// Join the game room
socket.emit('join', { game_id: GAME_ID });

// Ready button
const readyButton = document.createElement('button');
readyButton.className = 'btn btn-success mb-3';
readyButton.textContent = 'Ready to Start';
document.getElementById('gameStatus').after(readyButton);

readyButton.addEventListener('click', () => {
    socket.emit('player_ready', { game_id: GAME_ID });
    readyButton.disabled = true;
    readyButton.textContent = 'Waiting for others...';
});

// Socket event handlers
socket.on('player_joined', (data) => {
    const playersList = document.getElementById('playersList');
    const li = document.createElement('li');
    li.className = 'list-group-item';
    li.textContent = data.username;
    playersList.querySelector('ul').appendChild(li);
    
    document.getElementById('gameStatus').textContent = 
        `Waiting for players... (${data.player_count}/6)`;
});

socket.on('game_start', () => {
    document.getElementById('gameStatus').textContent = 'Game Started!';
    readyButton.style.display = 'none';
    document.getElementById('gameArea').style.display = 'block';
});

socket.on('sentence_submitted', (data) => {
    if (data.game_status === 'completed') {
        showGameComplete();
    } else {
        document.getElementById('lastWords').textContent = 
            `Previous sentence ended with: ${data.last_words}`;
        document.getElementById('sentence').value = '';
    }
});

// Submit sentence handler
document.getElementById('submitSentence').addEventListener('click', () => {
    const sentence = document.getElementById('sentence').value.trim();
    if (sentence) {
        socket.emit('submit_sentence', {
            game_id: GAME_ID,
            sentence: sentence
        });
        document.getElementById('submitSentence').disabled = true;
    }
});

function showGameComplete() {
    document.getElementById('gameArea').style.display = 'none';
    document.getElementById('gameComplete').style.display = 'block';
    // Fetch and display the complete story
    fetch(`/game/${GAME_ID}/story`)
        .then(response => response.json())
        .then(story => {
            const storyHtml = story.sentences.map(s => 
                `<p><strong>${s.author}:</strong> ${s.content}</p>`
            ).join('');
            document.getElementById('finalStory').innerHTML = storyHtml;
        });
}
