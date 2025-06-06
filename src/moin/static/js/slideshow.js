/* jslint browser: true, nomen: true */

let slideNo = 1;
const slides = document.getElementsByClassName('moin-slides');

function showSlide(n) {
    let i;
    slideNo = n;
    for (i = 0; i < slides.length; i++) {
        slides[i].style.display = 'none';
    }
    slides[slideNo - 1].style.display = 'block';
    }

function nextSlide() {
    if (slideNo < slides.length) {
        showSlide((slideNo += 1));
    }
}

function prevSlide() {
    if (slideNo > 1) {
        showSlide((slideNo -= 1));
    }
}

function lastSlide() {
    showSlide(slides.length);
}

document.addEventListener('keydown', (event) => {
    if (event.code === 'ArrowLeft') {
        prevSlide();
    }
    if (event.code === 'ArrowRight') {
        nextSlide();
    }
});

showSlide(slideNo);
