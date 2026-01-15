// Compass tracker - makes the compass needle follow the mouse cursor
// Works with any element using the .mascot-guide-container class

document.addEventListener('DOMContentLoaded', function() {
  // Find all mascot SVG img elements (works with any mascot container class)
  const svgImgs = document.querySelectorAll('.mascot-guide-container img');

  if (svgImgs.length === 0) return; // Exit if no mascots found

  // Initialize compass tracking for each mascot
  svgImgs.forEach(initializeCompass);

  function initializeCompass(svgImg) {
    if (!svgImg) return; // Exit if SVG not found

    // Load the SVG and replace the img with inline SVG
    fetch(svgImg.src)
      .then(response => response.text())
      .then(svgText => {
        // Create a container and parse the SVG
        const svgContainer = document.createElement('div');
        svgContainer.innerHTML = svgText;
        const svgElement = svgContainer.querySelector('svg');

        // Replace the img with the inline SVG
        svgImg.parentNode.replaceChild(svgElement, svgImg);

        // Ensure SVG has proper dimensions
        svgElement.style.width = '100%';
        svgElement.style.height = '100%';

        // Now we can access the compass needle
        const compassNeedle = svgElement.getElementById('compassNeedle');
        if (!compassNeedle) return;

        function updateCompassRotation(e) {
          // Get SVG element position
          const svgRect = svgElement.getBoundingClientRect();

          // Calculate center of compass in viewport coordinates
          const centerX = svgRect.left + (svgRect.width / 2);
          const centerY = svgRect.top + (svgRect.height / 2);

          // Get mouse position
          const mouseX = e.clientX;
          const mouseY = e.clientY;

          // Calculate angle from center to mouse
          const deltaX = mouseX - centerX;
          const deltaY = mouseY - centerY;
          const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);

          // Rotate compass needle (add 90 because atan2 starts from right, we want up to be 0)
          const rotation = angle + 90;

          // Apply rotation with smooth transition
          compassNeedle.style.transform = `rotate(${rotation}deg)`;
        }

        // Listen for mouse movement
        document.addEventListener('mousemove', updateCompassRotation);

        // Optional: Reset to north when mouse leaves the page
        document.addEventListener('mouseleave', function() {
          compassNeedle.style.transform = 'rotate(0deg)';
        });
      })
      .catch(error => console.error('Error loading SVG:', error));
  }
});
