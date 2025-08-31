import os
import cv2
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']  # 中文支持
plt.rcParams['axes.unicode_minus'] = False

def imread_unicode(path):
    import pathlib
    stream = pathlib.Path(path).open("rb")
    bytes_array = bytearray(stream.read())
    np_array = np.asarray(bytes_array, dtype=np.uint8)
    img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return img

def draw_grasp_rect(ax, pts, grasp_id=None):
    pts = np.vstack([pts, pts[0]])  # 闭合矩形
    for i in range(4):
        color = 'r' if i % 2 == 0 else 'b'
        ax.plot([pts[i][0], pts[i+1][0]], [pts[i][1], pts[i+1][1]], color=color, linewidth=2)
    if grasp_id is not None:
        ax.text(pts[0][0], pts[0][1], f'G{grasp_id}',
                color='green', fontsize=10, ha='center', va='bottom',
                bbox=dict(facecolor='white', edgecolor='green', alpha=0.6))

def load_grasp_rect(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    pts = np.array([[float(v) for v in line.strip().split()] for line in lines])
    return pts

class AnnotatedViewer:
    def __init__(self, image_dir, label_dir):
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.image_list = sorted([f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
        self.idx = 0
        self.dragging = False
        self.last_xy = None

        self.fig, self.ax = plt.subplots()
        self._connect_events()
        self._show_current()
        plt.show()

    def _connect_events(self):
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)

    def _show_current(self):
        self.ax.clear()
        if self.idx >= len(self.image_list):
            print("✅ 所有图像查看完毕")
            plt.close()
            return

        imgname = self.image_list[self.idx]
        img_path = os.path.join(self.image_dir, imgname)
        name_no_ext = os.path.splitext(imgname)[0]
        label_folder = os.path.join(self.label_dir, name_no_ext)
        jacquard_path = os.path.join(self.label_dir, name_no_ext + '_jacquard.txt')

        img = imread_unicode(img_path)
        if img is None:
            print(f"❌ 图像读取失败: {img_path}")
            self.idx += 1
            self._show_current()
            return

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.ax.imshow(img)
        self.ax.set_title(f"[{self.idx+1}/{len(self.image_list)}] {imgname} - ←/→:翻图 | 滚轮:缩放 | 右键:拖动 | ESC:退出")
        self.current_image = img

        if os.path.exists(label_folder):
            grasp_files = sorted([f for f in os.listdir(label_folder) if f.startswith('grasp_')])
            for i, fname in enumerate(grasp_files):
                rect_path = os.path.join(label_folder, fname)
                pts = load_grasp_rect(rect_path)
                draw_grasp_rect(self.ax, pts, grasp_id=i)

        if os.path.exists(jacquard_path):
            with open(jacquard_path, 'r', encoding='utf-8') as f:
                for line in f:
                    cx, cy, angle, w, h = map(float, line.strip().split())
                    self.ax.plot(cx, cy, 'gx')
                    self.ax.text(cx, cy, f'{angle:.1f}°', color='blue', fontsize=9)

        # 默认坐标范围
        self.ax.set_xlim(0, img.shape[1])
        self.ax.set_ylim(img.shape[0], 0)
        self.fig.canvas.draw()

    def on_key(self, event):
        if event.key == 'right':
            self.idx = min(self.idx + 1, len(self.image_list) - 1)
            self._show_current()
        elif event.key == 'left':
            self.idx = max(self.idx - 1, 0)
            self._show_current()
        elif event.key == 'escape':
            plt.close()

    def on_scroll(self, event):
        base_scale = 1.2
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        if xdata is None or ydata is None:
            return
        scale_factor = base_scale if event.button == 'up' else 1 / base_scale
        self.ax.set_xlim([xdata - (xdata - cur_xlim[0]) / scale_factor,
                          xdata + (cur_xlim[1] - xdata) / scale_factor])
        self.ax.set_ylim([ydata - (ydata - cur_ylim[0]) / scale_factor,
                          ydata + (cur_ylim[1] - ydata) / scale_factor])
        self.fig.canvas.draw()

    def on_press(self, event):
        if event.button == 3 and event.inaxes:  # 鼠标右键
            self.dragging = True
            self.last_xy = (event.x, event.y)

    def on_motion(self, event):
        if not self.dragging or self.last_xy is None:
            return
        dx = event.x - self.last_xy[0]
        dy = event.y - self.last_xy[1]
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        self.ax.set_xlim(cur_xlim[0] - dx, cur_xlim[1] - dx)
        self.ax.set_ylim(cur_ylim[0] + dy, cur_ylim[1] + dy)
        self.fig.canvas.draw()
        self.last_xy = (event.x, event.y)

    def on_release(self, event):
        if event.button == 3:
            self.dragging = False
            self.last_xy = None

# ============ 使用方式 ============
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--img_dir', required=True, help='图片文件夹路径')
    parser.add_argument('--label_dir', required=True, help='标注保存路径')
    args = parser.parse_args()

    AnnotatedViewer(args.img_dir, args.label_dir)
