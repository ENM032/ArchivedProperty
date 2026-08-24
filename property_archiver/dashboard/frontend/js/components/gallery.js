/**
 * Photo Gallery Carousel & Thumbnail Navigator Component.
 */
let currentImages = [];
let currentIndex = 0;
let currentListingId = '';

export function initGallery(listingId, images) {
    currentListingId = listingId;
    currentImages = images || [];
    currentIndex = 0;

    const container = document.getElementById('gallery-container');
    const strip = document.getElementById('gallery-thumb-strip');
    if (!container || !strip) return;

    if (currentImages.length === 0) {
        container.style.display = 'none';
        strip.style.display = 'none';
        return;
    }
    container.style.display = 'block';
    strip.style.display = 'flex';

    updateGalleryImage();

    strip.innerHTML = '';
    currentImages.forEach((img, idx) => {
        const item = document.createElement('div');
        item.className = `thumb-strip-item ${idx === currentIndex ? 'active' : ''}`;
        item.onclick = () => { currentIndex = idx; updateGalleryImage(); };
        const src = `/api/listings/${currentListingId}/image/${img.local_filename}`;
        item.innerHTML = `<img src="${src}" alt="Thumb ${idx + 1}">`;
        strip.appendChild(item);
    });

    document.getElementById('gallery-prev-btn').onclick = (e) => {
        e.stopPropagation();
        currentIndex = (currentIndex - 1 + currentImages.length) % currentImages.length;
        updateGalleryImage();
    };

    document.getElementById('gallery-next-btn').onclick = (e) => {
        e.stopPropagation();
        currentIndex = (currentIndex + 1) % currentImages.length;
        updateGalleryImage();
    };
}

function updateGalleryImage() {
    if (!currentImages[currentIndex]) return;
    const img = currentImages[currentIndex];
    const src = `/api/listings/${currentListingId}/image/${img.local_filename}`;
    document.getElementById('gallery-main-img').src = src;
    document.getElementById('gallery-counter').innerText = `${currentIndex + 1} / ${currentImages.length}`;

    const items = document.querySelectorAll('.thumb-strip-item');
    items.forEach((it, idx) => {
        it.classList.toggle('active', idx === currentIndex);
    });
}
