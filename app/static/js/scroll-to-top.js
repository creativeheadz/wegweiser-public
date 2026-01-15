document.addEventListener('DOMContentLoaded', function() {
    const button = document.createElement('button');
    button.className = 'back-to-top';
    button.setAttribute('aria-label', 'Scroll to top');
    button.innerHTML = '<span class="fa-solid fa-arrow-up"></span>';
    document.body.appendChild(button);

    function handleScroll() {
        requestAnimationFrame(() => {
            if (window.scrollY > 300) {
                button.classList.add('active');
                button.style.display = 'flex';
            } else {
                button.classList.remove('active');
                button.style.display = 'none';
            }
        });
    }

    window.addEventListener('scroll', handleScroll, { passive: true });

    button.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
});