// Level Up & Gamification JS

function showLevelUp(level, title) {
    var modal = document.createElement('div');
    modal.id = 'levelUpModal';
    modal.style.cssText = [
        'position: fixed',
        'inset: 0',
        'z-index: 9999',
        'display: flex',
        'align-items: center',
        'justify-content: center',
        'background: rgba(0,0,0,0.7)',
        'backdrop-filter: blur(10px)',
        'animation: fadeIn 0.3s ease'
    ].join(';');

    modal.innerHTML = [
        '<div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 24px; padding: 50px; text-align: center; max-width: 400px; box-shadow: 0 30px 60px rgba(0,0,0,0.5); animation: slideUp 0.5s cubic-bezier(0.16,1,0.3,1);">',
            '<div style="font-size: 4rem; margin-bottom: 15px;">🎉</div>',
            '<h2 style="font-size: 1.8rem; margin-bottom: 8px; background: linear-gradient(135deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Daraja ko\'tarildi!</h2>',
            '<div style="font-size: 3rem; font-weight: 900; color: var(--primary); margin: 15px 0;">' + level + '</div>',
            '<p style="font-size: 1.2rem; color: var(--text-main); margin-bottom: 20px;">Yangi unvon: <strong>' + title + '</strong></p>',
            '<button onclick="closeLevelUp()" class="btn-primary" style="padding: 12px 40px; border-radius: 14px; border: none; cursor: pointer; font-size: 1rem; font-weight: 700;">Ajoyib! 🚀</button>',
        '</div>'
    ].join('');

    document.body.appendChild(modal);

    // Confetti effect
    if (typeof confetti === 'function') {
        var duration = 3000;
        var end = Date.now() + duration;
        (function frame() {
            confetti({
                particleCount: 7,
                spread: 80,
                origin: { y: 0.6 },
                colors: ['#6366f1', '#a855f7', '#f59e0b', '#10b981', '#ec4899']
            });
            if (Date.now() < end) {
                requestAnimationFrame(frame);
            }
        })();
    }
}

function closeLevelUp() {
    var modal = document.getElementById('levelUpModal');
    if (modal) modal.remove();
}

// Check QR scan response for level up
function checkLevelUpResponse(data) {
    if (data.leveled_up && data.new_level) {
        var titles = ['', 'Новичок', 'Читатель', 'Книголюб', 'Начитанный', 'Книжный червь', 'Эрудит', 'Интеллектуал', 'Профессор', 'Мудрец', 'Легенда'];
        showLevelUp(data.new_level, titles[data.new_level] || 'Level ' + data.new_level);
    }
    if (data.new_achievements && data.new_achievements.length > 0) {
        showAchievementNotification(data.new_achievements);
    }
}

function showAchievementNotification(achievements) {
    if (achievements.length === 0) return;
    var names = achievements.join(', ');
    var notification = document.createElement('div');
    notification.style.cssText = [
        'position: fixed',
        'bottom: 20px',
        'right: 20px',
        'z-index: 9998',
        'background: var(--bg-card)',
        'border: 1px solid rgba(251,191,36,0.3)',
        'border-radius: 16px',
        'padding: 20px 25px',
        'box-shadow: 0 10px 30px rgba(0,0,0,0.5)',
        'animation: slideUp 0.5s cubic-bezier(0.16,1,0.3,1)',
        'max-width: 350px'
    ].join(';');
    notification.innerHTML = [
        '<div style="display: flex; align-items: center; gap: 15px;">',
            '<div style="font-size: 2rem;">🏆</div>',
            '<div>',
                '<div style="font-size: 0.75rem; color: #fbbf24; font-weight: 700; text-transform: uppercase;">Yangi yutuq!</div>',
                '<div style="font-weight: 600; margin-top: 3px;">' + names + '</div>',
            '</div>',
        '</div>'
    ].join('');
    document.body.appendChild(notification);
    setTimeout(function() { notification.remove(); }, 5000);
}
