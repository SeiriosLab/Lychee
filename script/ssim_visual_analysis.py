
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from skimage.metrics import structural_similarity as ssim
from itertools import combinations

def load_images_from_folder(folder, max_images=None):
    images = []
    filenames = []
    for filename in sorted(os.listdir(folder)):
        if filename.lower().endswith(".jpg"):
            img_path = os.path.join(folder, filename)
            img = cv2.imread(img_path)
            if img is not None:
                images.append(img)
                filenames.append(filename)
            if max_images and len(images) >= max_images:
                break
    return images, filenames

def compute_ssim(img1, img2):
    img1 = cv2.resize(img1, (128, 128))
    img2 = cv2.resize(img2, (128, 128))
    if len(img1.shape) == 3:
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    else:
        gray1, gray2 = img1, img2
    score = ssim(gray1, gray2, data_range=255)
    return score

# def analyze_similarity_scores(scores):
#     plt.figure(figsize=(14, 5))

#     # 左图：盒式图（X 为索引，Y 为 SSIM）
#     plt.subplot(1, 2, 1)
#     sns.boxplot(data=scores, orient='v', color='orange')
#     plt.title('SSIM Boxplot (All Pairs)')
#     plt.ylabel('SSIM Score')
#     plt.xlabel('Pair Index (Box Summary)')

#     # 右图：KDE 曲线图
#     plt.subplot(1, 2, 2)
#     sns.kdeplot(scores, fill=True, color='green')
#     plt.title('SSIM KDE (Density Estimation)')
#     plt.xlabel('SSIM Score')
#     plt.ylabel('Density')

#     plt.tight_layout()
#     plt.show()

def analyze_similarity_scores(scores):
    plt.figure(figsize=(14, 5))

    # 左图：散点图（每对图像的 SSIM 分数）
    plt.subplot(1, 2, 1)
    plt.scatter(range(len(scores)), scores, color='orange', s=20)
    plt.title('SSIM Score per Image Pair')
    plt.xlabel('Pair Index')
    plt.ylabel('SSIM Score')
    plt.grid(True)

    # 右图：KDE 曲线图
    plt.subplot(1, 2, 2)
    sns.kdeplot(scores, fill=True, color='green')
    plt.title('SSIM KDE (Density Estimation)')
    plt.xlabel('SSIM Score')
    plt.ylabel('Density')

    plt.tight_layout()
    plt.show()

def main():
    folder = r"E:\Datasets\litchi\data_open\LitchiDG\250619"  # 替换成你的图像路径
    images, filenames = load_images_from_folder(folder)
    print(f"Loaded {len(images)} images.")

    ssim_scores = []

    for (i1, img1), (i2, img2) in combinations(enumerate(images), 2):
        score = compute_ssim(img1, img2)
        ssim_scores.append(score)
        print(f"SSIM between {filenames[i1]} and {filenames[i2]} = {score:.4f}")

    analyze_similarity_scores(ssim_scores)

if __name__ == "__main__":
    main()
