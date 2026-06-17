import os

# The folders for your new categories
folders = ['surreal', 'minimalist', 'cyberpunk', 'fluid']
base_dir = os.path.dirname(os.path.abspath(__file__))

for category in folders:
    folder_path = os.path.join(base_dir, category)
    
    # Skip if the folder doesn't exist
    if not os.path.exists(folder_path):
        print(f"Folder '{category}' not found. Skipping.")
        continue
        
    print(f"\n--- Renaming {category} ---")
    
    # Grab all files in the folder
    files = os.listdir(folder_path)
    # Filter out hidden system files to be safe
    images = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    
    for index, filename in enumerate(images, start=1):
        # Keep the original extension (.png or .jpeg)
        file_ext = os.path.splitext(filename)[1] 
        
        # Create the exact new name: e.g., "cyberpunk1.png"
        new_name = f"{category}{index}{file_ext}"
        
        old_path = os.path.join(folder_path, filename)
        new_path = os.path.join(folder_path, new_name)
        
        # Actually rename the file
        os.rename(old_path, new_path)
        print(f"Renamed: {filename} -> {new_name}")

print("\nBatch rename complete! Ready for Cloudinary.")