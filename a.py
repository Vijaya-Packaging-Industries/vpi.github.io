import cv2
import numpy as np

def convert_to_svg_omit_black(image_path, output_path, n_colors=5):
    print(f"--- Processing {image_path} ---")
    
    # 1. Load Image with Alpha Channel
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    
    if img is None:
        print("Error: Could not load image. Check the file name.")
        return

    # 2. Force Transparent Background to Black
    # We want to ensure the "background" is a color we can easily remove later.
    if img.shape[2] == 4:
        print("Transparency detected. Converting background to BLACK...")
        # Create a mask where alpha is transparent (0)
        alpha = img[:, :, 3]
        
        # Convert to BGR (discard alpha channel)
        img_bgr = img[:, :, :3]
        
        # Everywhere the alpha is 0, make the pixel pure black [0,0,0]
        img_bgr[alpha == 0] = [0, 0, 0]
        
        img = img_bgr
    else:
        print("No transparency found. Assuming background is already black or dark.")

    height, width = img.shape[:2]

    # 3. Smooth the Image (Remove Texture)
    print("Smoothing texture...")
    # Median Blur to remove grain
    blurred = cv2.medianBlur(img, 9)
    
    # Mean Shift to flatten colors (posterize)
    # We process on a smaller scale for speed if the image is huge
    if width > 800:
        scale = 800 / width
        small = cv2.resize(blurred, (0, 0), fx=scale, fy=scale)
        filtered_small = cv2.pyrMeanShiftFiltering(small, sp=25, sr=50)
        filtered = cv2.resize(filtered_small, (width, height))
    else:
        filtered = cv2.pyrMeanShiftFiltering(blurred, sp=25, sr=50)

    # 4. Color Grouping (K-Means)
    print(f"Grouping colors into {n_colors} main shades...")
    data = filtered.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(data, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    centers = np.uint8(centers)
    quantized = centers[labels.flatten()].reshape(filtered.shape)

    # 5. Generate SVG & OMIT BLACK
    print("Tracing paths (Ignoring Black Background)...")
    svg_lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">']

    for i in range(n_colors):
        # Get the color for this group
        b, g, r = centers[i]
        
        # --- THE FIX: OMIT BLACK ---
        # If the color is very dark (sum of R+G+B is low), we skip it.
        # This prevents drawing the "box" around your logo.
        if (int(b) + int(g) + int(r)) < 40: 
            print(f"  Skipping dark background color: RGB({r},{g},{b})")
            continue
            
        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
        
        # Create mask for this color
        mask = cv2.inRange(quantized, centers[i], centers[i])
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            # Filter noise
            if cv2.contourArea(cnt) < 100: continue

            # Smooth contour
            epsilon = 0.002 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            
            # Write Path
            points = approx.reshape(-1, 2)
            if len(points) > 2:
                path_d = "M " + " ".join([f"{p[0]},{p[1]}" for p in points]) + " Z"
                svg_lines.append(f'<path d="{path_d}" fill="{hex_color}" stroke="none" />')

    svg_lines.append('</svg>')

    # 6. Save
    with open(output_path, "w") as f:
        f.write("\n".join(svg_lines))
    
    print(f"Success! SVG saved to: {output_path}")

# --- Run the function ---
if __name__ == "__main__":
    # Ensure your file is named 'logo.png'
    convert_to_svg_omit_black('logo.png', 'logo_final.svg', n_colors=5)
