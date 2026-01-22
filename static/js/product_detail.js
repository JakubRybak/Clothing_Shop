let currentImageIndex = 0;
let productImages = [];

// Initialize images from data attribute when page loads
document.addEventListener('DOMContentLoaded', () => {
    const mainImg = document.getElementById('main-image');
    if (mainImg && mainImg.dataset.images) {
        productImages = JSON.parse(mainImg.dataset.images);
    }
});

function updateMainImage() {
    const img = document.getElementById('main-image');
    if (img && productImages.length > 0 && productImages[currentImageIndex]) {
        img.src = productImages[currentImageIndex];
    }
}

function setImage(index) {
    currentImageIndex = index;
    updateMainImage();
}

function nextImage() {
    if (typeof productImages !== 'undefined' && productImages.length > 0) {
        currentImageIndex = (currentImageIndex + 1) % productImages.length;
        updateMainImage();
    }
}

function prevImage() {
    if (typeof productImages !== 'undefined' && productImages.length > 0) {
        currentImageIndex = (currentImageIndex - 1 + productImages.length) % productImages.length;
        updateMainImage();
    }
}