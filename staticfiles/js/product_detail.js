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

// Add-to-Cart Button Animation Logic
document.addEventListener('DOMContentLoaded', function() {
    const addToCartBtn = document.getElementById('add-to-cart-btn');

    if (addToCartBtn) {
        // Store original text
        let originalText = addToCartBtn.innerHTML;

        // Ensure smooth color transition
        addToCartBtn.style.transition = 'all 0.3s ease';

        addToCartBtn.addEventListener('htmx:configRequest', function() {
            // Loading State
            addToCartBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Adding...'; 
            addToCartBtn.disabled = true;
        });

        addToCartBtn.addEventListener('htmx:afterOnLoad', function(evt) {
            if (evt.detail.xhr.status === 200) {
                // Success State
                addToCartBtn.classList.remove('btn-primary');
                addToCartBtn.classList.add('btn-success');
                addToCartBtn.innerHTML = 'Added to Cart! <span class="fw-bold">✓</span>';

                // Revert after 2 seconds
                setTimeout(() => {
                    addToCartBtn.classList.remove('btn-success');
                    addToCartBtn.classList.add('btn-primary');
                    addToCartBtn.innerHTML = originalText;
                    addToCartBtn.disabled = false;
                }, 2000);
            } else {
                // Error State (optional, revert immediately)
                addToCartBtn.innerHTML = originalText;
                addToCartBtn.disabled = false;
            }
        });
    }
});