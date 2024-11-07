const socket = io();
const room = `game_${GAME_ID}`;
let myTurn = false;

// Join the game room
socket.emit('join', { game_id: GAME_ID });

// Ready button handler
const readyButton = document.getElementById('readyButton');
if (readyButton) {
    readyButton.addEventListener('click', () => {
        socket.emit('player_ready', { game_id: GAME_ID });
        readyButton.disabled = true;
        readyButton.textContent = 'Waiting for others...';
    });
}

// Copy share link
function copyShareLink() {
    const shareLink = document.getElementById('shareLink');
    shareLink.select();
    document.execCommand('copy');
    
    // Visual feedback
    const button = shareLink.nextElementSibling;
    const originalText = button.textContent;
    button.textContent = 'Copied!';
    setTimeout(() => button.textContent = originalText, 2000);
}

// Socket event handlers
socket.on('game_status', (data) => {
    document.getElementById('playerCount').textContent = data.player_count;
    document.getElementById('totalPlayers').textContent = data.player_count;
    
    // Update ready status for all players
    const playersList = document.getElementById('playersList');
    data.players.forEach(player => {
        const playerItem = playersList.querySelector(`[data-player="${player.username}"]`);
        if (playerItem) {
            const badge = playerItem.querySelector('.ready-status');
            badge.textContent = player.ready ? 'Ready' : 'Not Ready';
            badge.className = `badge ${player.ready ? 'bg-success' : 'bg-secondary'} ready-status`;
        }
    });
});

socket.on('player_status_update', (data) => {
    document.getElementById('readyCount').textContent = data.ready_count;
    
    const playerItem = document.querySelector(`[data-player="${data.username}"]`);
    if (playerItem) {
        const badge = playerItem.querySelector('.ready-status');
        badge.textContent = data.ready ? 'Ready' : 'Not Ready';
        badge.className = `badge ${data.ready ? 'bg-success' : 'bg-secondary'} ready-status`;
    }
});

socket.on('game_start', (data) => {
    document.getElementById('gameStatus').textContent = 'Game Started!';
    document.getElementById('readyButton')?.remove();
    document.getElementById('gameArea').style.display = 'block';
    
    updateTurnProgress(data.current_turn);
    
    if (data.first_turn) {
        document.getElementById('lastWords').textContent = 'Start the story!';
        document.getElementById('turnIndicator').textContent = "It's your turn to start the story!";
        document.getElementById('sentence').disabled = false;
        document.getElementById('submitSentence').disabled = false;
    }
});

socket.on('sentence_submitted', (data) => {
    if (data.game_status === 'completed') {
        showGameComplete();
    } else {
        document.getElementById('lastWords').textContent = 
            `Previous sentence ended with: ${data.last_words}`;
        document.getElementById('sentence').value = '';
        updateTurnProgress(data.turn);
        
        // Update turn indicator
        const turnIndicator = document.getElementById('turnIndicator');
        const isMyTurn = data.next_player === document.querySelector('.navbar-nav .text-light').textContent.trim();
        
        if (isMyTurn) {
            turnIndicator.textContent = "It's your turn!";
            document.getElementById('sentence').disabled = false;
            document.getElementById('submitSentence').disabled = false;
        } else {
            turnIndicator.textContent = `Waiting for ${data.next_player} to write...`;
            document.getElementById('sentence').disabled = true;
            document.getElementById('submitSentence').disabled = true;
        }
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
        document.getElementById('sentence').disabled = true;
    }
});

function updateTurnProgress(turn) {
    const progress = (turn / 12) * 100;
    const progressBar = document.getElementById('turnProgress');
    progressBar.style.width = `${progress}%`;
    progressBar.textContent = `Turn ${turn}/12`;
}

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
