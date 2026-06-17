// localfs/static/js/main.js

// This function runs once the entire HTML document is loaded and ready.
$(document).ready(function() {
    
    // Select the search input element by its ID.
    const searchInput = $('#searchInput');
    // Select all file card elements.
    const fileCards = $('.file-card');
    // Select the "no results" message element.
    const noResultsMessage = $('#no-results');

    // Attach an event listener that triggers on every key press in the search input.
    searchInput.on('keyup', function() {
        // Get the current value of the search input and convert it to lower case for case-insensitive matching.
        const searchTerm = $(this).val().toLowerCase();
        
        // A counter to track how many files are visible.
        let visibleFiles = 0;

        // Iterate over each file card.
        fileCards.each(function() {
            // Get the filename from the 'data-filename' attribute we set in the HTML.
            const filename = $(this).data('filename');

            // Check if the filename includes the search term.
            if (filename.includes(searchTerm)) {
                // If it matches, show the card with a fade-in effect.
                $(this).fadeIn();
                // Increment the visible file counter.
                visibleFiles++;
            } else {
                // If it doesn't match, hide the card with a fade-out effect.
                $(this).fadeOut();
            }
        });

        // After checking all cards, see if any are visible.
        if (visibleFiles === 0 && fileCards.length > 0) {
            // If no files are visible (and there were files to begin with), show the "no results" message.
            noResultsMessage.show();
        } else {
            // Otherwise, hide the message.
            noResultsMessage.hide();
        }
    });
});
