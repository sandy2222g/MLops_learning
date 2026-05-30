import json
import os
import shutil
from pathlib import Path
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

def convert_labelme_to_yolo(json_file, output_dir, image_dir):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        image_height = data['imageHeight']
        image_width = data['imageWidth']
        
        txt_file = os.path.splitext(os.path.basename(json_file))[0] + '.txt'
        txt_path = os.path.join(output_dir, txt_file)
        
        with open(txt_path, 'w') as f:
            for shape in data['shapes']:
                if shape['shape_type'] != 'polygon':
                    continue  
                
                category = shape['label']
                polygon = shape['points']
                
                normalized_polygon = []
                for x, y in polygon:
                    normalized_polygon.extend([x / image_width, y / image_height])
                
                f.write(f"{category} {' '.join(map(str, normalized_polygon))}\n")
        
        image_file = data['imagePath']
        src_image = os.path.join(image_dir, image_file)
        dst_image = os.path.join(output_dir, image_file)
        
        if os.path.exists(src_image):
            shutil.copy(src_image, dst_image)
        else:
            print(f"Image not found: {src_image}")
        
        return True
    except Exception as e:
        print(f"Error processing {json_file}: {str(e)}")
        return False

def create_dataset_split(input_dir, output_dir, split_ratio=(0.7, 0.2, 0.1)):
    files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
    random.shuffle(files)
    
    train_split = int(len(files) * split_ratio[0])
    val_split = int(len(files) * (split_ratio[0] + split_ratio[1]))
    
    train_files = files[:train_split]
    val_files = files[train_split:val_split]
    test_files = files[val_split:]
    
    for split, file_list in [('train', train_files), ('val', val_files), ('test', test_files)]:
        split_dir = os.path.join(output_dir, split)
        os.makedirs(split_dir, exist_ok=True)
        for file in file_list:
            txt_src = os.path.join(input_dir, file)
            img_src = os.path.join(input_dir, os.path.splitext(file)[0] + '.jpg')  # Assuming .jpg images
            
            txt_dst = os.path.join(split_dir, file)
            img_dst = os.path.join(split_dir, os.path.splitext(file)[0] + '.jpg')
            
            if os.path.exists(txt_src) and os.path.exists(img_src):
                shutil.copy(txt_src, txt_dst)
                shutil.copy(img_src, img_dst)
            else:
                print(f"Missing file: {txt_src} or {img_src}")

def process_files(json_files, output_dir, image_dir):
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(convert_labelme_to_yolo, str(json_file), output_dir, image_dir) 
                   for json_file in json_files]
        
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Converting files"):
            pass

def main():
    json_dir = r'D:\smartcity_dataset\json_dir'
    image_dir = r'D:\smartcity_dataset\img_dir'
    output_dir = r'D:\smartcity_dataset\outputdir'
    final_dataset_dir = r'D:\smartcity_dataset\final_dataset'

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(final_dataset_dir, exist_ok=True)

    json_files = list(Path(json_dir).glob('*.json'))
    total_files = len(json_files)
    
    print(f"Total JSON files found: {total_files}")
    
    # Process files in batches of 15000
    batch_size = 15000
    for i in range(0, total_files, batch_size):
        batch = json_files[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1} of {(total_files-1)//batch_size + 1}")
        process_files(batch, output_dir, image_dir)

    print("Conversion completed. Starting dataset splitting...")
    create_dataset_split(output_dir, final_dataset_dir)
    print("Dataset splitting completed.")

if __name__ == "__main__":
    main()