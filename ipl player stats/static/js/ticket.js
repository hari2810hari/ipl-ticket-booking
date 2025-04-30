document.addEventListener('DOMContentLoaded', function() {
    const standTierSelect = document.getElementById('stand_tier');
    const seatSelection = document.getElementById('seatSelection');
    const standTitle = document.getElementById('standTitle');
    const bookButton = document.getElementById('bookButton');
    const seatGrid = document.getElementById('seatGrid');
    const allSeats = document.querySelectorAll('.seat');

    // Stand tier selection handler
    standTierSelect.addEventListener('change', function() {
        const selectedTier = this.value;

        if (selectedTier) {
            // Show seat selection
            seatSelection.style.display = 'block';

            // Update stand title
            const tierNames = {
                'premium': 'Premium Stand Seats (₹1500 per seat)',
                'standard': 'Standard Stand Seats (₹1000 per seat)',
                'economy': 'Economy Stand Seats (₹500 per seat)'
            };
            standTitle.textContent = tierNames[selectedTier];

            // Filter seats by tier
            allSeats.forEach(seat => {
                const seatTier = seat.dataset.tier;
                if (seatTier === selectedTier) {
                    seat.style.display = 'flex';
                } else {
                    seat.style.display = 'none';
                }
            });

            // Enable book button
            bookButton.disabled = false;
        } else {
            seatSelection.style.display = 'none';
            bookButton.disabled = true;
        }
    });

    // Seat selection handler
    seatGrid.addEventListener('click', function(e) {
        const seatLabel = e.target.closest('.seat');
        if (!seatLabel || seatLabel.classList.contains('booked')) return;

        const checkbox = seatLabel.querySelector('input[type="checkbox"]');
        if (checkbox) {
            checkbox.checked = !checkbox.checked;
            seatLabel.classList.toggle('selected', checkbox.checked);
        }
    });

    // Show modal after successful booking
    {% if request.method == 'POST' %}
        const modal = new bootstrap.Modal(document.getElementById('confirmationModal'));
        modal.show();
    {% endif %}
});