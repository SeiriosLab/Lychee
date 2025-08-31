import os
import cv2
import numpy as np
import argparse
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def imread_unicode(path):
    import pathlib
    stream = pathlib.Path(path).open("rb")
    bytes_array = bytearray(stream.read())
    np_array = np.asarray(bytes_array, dtype=np.uint8)
    img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return img

def get_rotated_rect(x, y, w, h, angle_deg):
    rad = np.deg2rad(angle_deg)
    box = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
    R = np.array([[np.cos(rad), -np.sin(rad)], [np.sin(rad), np.cos(rad)]])
    return (R @ box.T).T + np.array([x, y])

def draw_rect(ax, pts, angle_deg, jacquard_angle, grasp_id=None):
    pts = np.vstack([pts, pts[0]])
    for i in range(4):
        color = 'r' if i % 2 == 0 else 'b'
        ax.plot([pts[i][0], pts[i+1][0]], [pts[i][1], pts[i+1][1]], color=color, linewidth=2)
    for i in range(4):
        ax.text(pts[i][0], pts[i][1], str(i),
                color='black', fontsize=10, ha='center', va='center',
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='circle'))
    if grasp_id is not None:
        start = pts[0]
        offset_x = 20 * np.cos(np.deg2rad(angle_deg))
        offset_y = 20 * np.sin(np.deg2rad(angle_deg))
        ax.text(start[0] + offset_x, start[1] + offset_y,
                f'G{grasp_id}: {jacquard_angle:.1f}°',
                color='darkgreen', fontsize=10, ha='left', va='bottom',
                bbox=dict(facecolor='white', edgecolor='green', alpha=0.6))

class AnnotatorUI:
    def __init__(self, img_dir, save_dir):
        self.img_files = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
        self.img_dir = img_dir
        self.save_dir = save_dir
        self.cur_idx = 0
        self.clicks = []
        self.rect_idx = 0
        self.text_handles = []
        self._run_next_image()

    def _run_next_image(self):
        if self.cur_idx >= len(self.img_files):
            print("✅ 所有图片标注完成！")
            return
        self.clicks = []
        self.rect_idx = 0
        self.text_handles.clear()
        imgname = self.img_files[self.cur_idx]
        self.img_path = os.path.join(self.img_dir, imgname)
        self.imgname = os.path.splitext(imgname)[0]
        self.image = imread_unicode(self.img_path)
        if self.image is None:
            print(f"❌ 图像读取失败：{self.img_path}")
            self.cur_idx += 1
            self._run_next_image()
            return
        self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        self.cornell_dir = os.path.join(self.save_dir, self.imgname)
        os.makedirs(self.cornell_dir, exist_ok=True)
        self.jacquard_path = os.path.join(self.save_dir, self.imgname + '_jacquard.txt')
        self.jacquard_file = open(self.jacquard_path, 'a', encoding='utf-8')

        self.fig, self.ax = plt.subplots()
        self.ax.imshow(self.image)
        self._update_title()
        self.drawn = []
        self.cid_click = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.cid_key = self.fig.canvas.mpl_connect('key_press_event', self.onkey)
        self.cid_scroll = self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.cid_motion = self.fig.canvas.mpl_connect('motion_notify_event', self.on_drag)
        self.cid_release = self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.dragging = False
        self.last_xy = None
        plt.tight_layout()
        plt.show()

    def _update_title(self):
        self.ax.set_title(f'[{self.cur_idx+1}/{len(self.img_files)}] {self.img_files[self.cur_idx]}\n'
                          '🖱️ 左键标注三点 | 鼠标右键拖动平移 | 滚轮缩放 | n: 下一张 | esc: 取消当前 | d: 删除上一个')

    def onclick(self, event: MouseEvent):
        if event.inaxes != self.ax:
            return
        if event.button == 3:  # Right-click
            self.dragging = True
            self.last_xy = (event.x, event.y)
            return
        if event.button != 1:
            return
        self.clicks.append([event.xdata, event.ydata])
        print(f"🟠 点击第 {len(self.clicks)} 点: ({event.xdata:.1f}, {event.ydata:.1f})")
        handle = self.ax.plot(event.xdata, event.ydata, 'ro')[0]
        text = self.ax.text(event.xdata, event.ydata, str(len(self.clicks)-1),
                            color='black', fontsize=10, ha='center', va='center',
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='circle'))
        self.text_handles.append((handle, text))
        self.ax.figure.canvas.draw()

        if len(self.clicks) == 3:
            x, y = self.clicks[0]
            x2, y2 = self.clicks[1]
            x3, y3 = self.clicks[2]
            w = np.hypot(x2 - x, y2 - y)
            h = np.hypot(x3 - x2, y3 - y2)
            angle = np.rad2deg(np.arctan2(y2 - y, x2 - x))
            jacquard_angle = -angle if angle <= 0 else 180 - angle
            rad = np.arctan2(y2 - y, x2 - x)
            rect_pts = get_rotated_rect(x, y, w, h, angle)

            draw_rect(self.ax, rect_pts, angle, jacquard_angle, self.rect_idx)
            self.ax.figure.canvas.draw()
            self.drawn.append((rect_pts, angle, jacquard_angle))

            with open(os.path.join(self.cornell_dir, f'grasp_{self.rect_idx:03d}.txt'), 'w', encoding='utf-8') as f:
                for pt in rect_pts:
                    f.write(f'{pt[0]:.2f} {pt[1]:.2f}\n')

            cx = x + np.cos(rad) * (w / 2)
            cy = y + np.sin(rad) * (w / 2)
            self.jacquard_file.write(f'{cx:.2f} {cy:.2f} {jacquard_angle:.5f} {w:.2f} {h:.2f}\n')
            self.jacquard_file.flush()

            print(f"✅ 保存 grasp {self.rect_idx}")
            self.rect_idx += 1
            self.clicks.clear()
            for h, t in self.text_handles:
                h.remove()
                t.remove()
            self.text_handles.clear()

    def on_drag(self, event):
        if self.dragging and self.last_xy:
            dx = event.x - self.last_xy[0]
            dy = event.y - self.last_xy[1]
            cur_xlim = self.ax.get_xlim()
            cur_ylim = self.ax.get_ylim()
            self.ax.set_xlim(cur_xlim[0] - dx, cur_xlim[1] - dx)
            self.ax.set_ylim(cur_ylim[0] + dy, cur_ylim[1] + dy)
            self.ax.figure.canvas.draw()
            self.last_xy = (event.x, event.y)

    def on_release(self, event):
        if event.button == 3:
            self.dragging = False
            self.last_xy = None

    def on_scroll(self, event):
        base_scale = 1.2
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        scale_factor = base_scale if event.button == 'up' else 1 / base_scale
        self.ax.set_xlim([xdata - (xdata - cur_xlim[0]) / scale_factor,
                          xdata + (cur_xlim[1] - xdata) / scale_factor])
        self.ax.set_ylim([ydata - (ydata - cur_ylim[0]) / scale_factor,
                          ydata + (cur_ylim[1] - ydata) / scale_factor])
        self.ax.figure.canvas.draw()

    def onkey(self, event):
        if event.key == 'n':
            self.jacquard_file.close()
            plt.close(self.fig)
            self.cur_idx += 1
            self._run_next_image()
        elif event.key == 'escape':
            print("🚫 取消当前 grasp")
            self.clicks.clear()
            for h, t in self.text_handles:
                h.remove()
                t.remove()
            self.text_handles.clear()
            self._redraw_all()
        elif event.key == 'd' and self.rect_idx > 0:
            print(f"🗑️ 删除 grasp {self.rect_idx - 1}")
            self.rect_idx -= 1
            os.remove(os.path.join(self.cornell_dir, f'grasp_{self.rect_idx:03d}.txt'))
            self._truncate_last_line(self.jacquard_path)
            self.drawn.pop()
            self._redraw_all()

    def _truncate_last_line(self, filepath):
        with open(filepath, 'rb+') as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell() - 1
            while pos > 0 and f.read(1) != b'\n':
                pos -= 1
                f.seek(pos, os.SEEK_SET)
            f.truncate(pos + 1)

    def _redraw_all(self):
        self.ax.clear()
        self.ax.imshow(self.image)
        self._update_title()
        for idx, (pts, angle, jacquard_angle) in enumerate(self.drawn):
            draw_rect(self.ax, pts, angle, jacquard_angle, idx)
        self.ax.figure.canvas.draw()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--img_dir', required=True, help='图片文件夹路径')
    parser.add_argument('--save_dir', required=True, help='标注保存路径')
    args = parser.parse_args()
    os.makedirs(args.save_dir, exist_ok=True)
    AnnotatorUI(args.img_dir, args.save_dir)




#
#
# import os
# import cv2
# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.widgets import RectangleSelector
# from matplotlib.backend_bases import MouseEvent
#
# # 设置中文字体（防止中文乱码）
# plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
# plt.rcParams['axes.unicode_minus'] = False
#
# def imread_unicode(path):
#     import pathlib
#     stream = pathlib.Path(path).open("rb")
#     bytes_array = bytearray(stream.read())
#     np_array = np.asarray(bytes_array, dtype=np.uint8)
#     img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
#     return img
#
# def get_rotated_rect(x, y, w, h, angle_deg):
#     rad = np.deg2rad(angle_deg)
#     box = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
#     R = np.array([[np.cos(rad), -np.sin(rad)], [np.sin(rad), np.cos(rad)]])
#     return (R @ box.T).T + np.array([x, y])
#
# def draw_rect(ax, pts, angle_deg,jacquard_angle, grasp_id=None):
#     pts = np.vstack([pts, pts[0]])
#     for i in range(4):
#         color = 'r' if i % 2 == 0 else 'b'
#         ax.plot([pts[i][0], pts[i+1][0]],
#                 [pts[i][1], pts[i+1][1]], color=color, linewidth=2)
#
#     for i in range(4):
#         ax.text(pts[i][0], pts[i][1], str(i),
#                 color='black', fontsize=10, ha='center', va='center',
#                 bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='circle'))
#
#     if grasp_id is not None:
#         start = pts[0]
#         offset_x = 20 * np.cos(np.deg2rad(angle_deg))
#         offset_y = 20 * np.sin(np.deg2rad(angle_deg))
#         ax.text(start[0] + offset_x, start[1] + offset_y,
#                 f'G{grasp_id}: {jacquard_angle:.1f}°',
#                 color='darkgreen', fontsize=10, ha='left', va='bottom',
#                 bbox=dict(facecolor='white', edgecolor='green', alpha=0.6))
#
# class AnnotatorUI:
#     def __init__(self, img_dir, save_dir):
#         self.img_files = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
#         self.img_dir = img_dir
#         self.save_dir = save_dir
#         self.cur_idx = 0
#         self.clicks = []
#         self.rect_idx = 0
#         self.text_handles = []
#         self._run_next_image()
#
#     def _run_next_image(self):
#         if self.cur_idx >= len(self.img_files):
#             print("✅ 所有图片标注完成！")
#             return
#         self.clicks = []
#         self.rect_idx = 0
#         self.text_handles.clear()
#
#         imgname = self.img_files[self.cur_idx]
#         self.img_path = os.path.join(self.img_dir, imgname)
#         self.imgname = os.path.splitext(imgname)[0]
#         self.image = imread_unicode(self.img_path)
#         if self.image is None:
#             print(f"❌ 图像读取失败：{self.img_path}")
#             self.cur_idx += 1
#             self._run_next_image()
#             return
#         self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
#         self.cornell_dir = os.path.join(self.save_dir, self.imgname)
#         os.makedirs(self.cornell_dir, exist_ok=True)
#         self.jacquard_path = os.path.join(self.save_dir, self.imgname + '_jacquard.txt')
#         self.jacquard_file = open(self.jacquard_path, 'a', encoding='utf-8')
#
#         self.fig, self.ax = plt.subplots()
#         self.ax.imshow(self.image)
#         self._update_title()
#         self.drawn = []
#         self.cid_click = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
#         self.cid_key = self.fig.canvas.mpl_connect('key_press_event', self.onkey)
#         self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
#         plt.tight_layout()
#         plt.show()
#
#     def _update_title(self):
#         self.ax.set_title(
#             f'[{self.cur_idx+1}/{len(self.img_files)}] {self.img_files[self.cur_idx]}\n'
#             '🖱️ 顺时针单击三点绘制抓取框 | n: 下一张 | esc: 取消当前 | d: 删除上一个')
#
#     def onclick(self, event: MouseEvent):
#         if event.inaxes != self.ax or event.button != 1:
#             return
#         self.clicks.append([event.xdata, event.ydata])
#         print(f"🟠 点击第 {len(self.clicks)} 点: ({event.xdata:.1f}, {event.ydata:.1f})")
#         handle = self.ax.plot(event.xdata, event.ydata, 'ro')[0]
#         text = self.ax.text(event.xdata, event.ydata, str(len(self.clicks)-1),
#                             color='black', fontsize=10, ha='center', va='center',
#                             bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, boxstyle='circle'))
#         self.text_handles.append((handle, text))
#         self.ax.figure.canvas.draw()
#
#         if len(self.clicks) == 3:
#             x, y = self.clicks[0]
#             x2, y2 = self.clicks[1]
#             x3, y3 = self.clicks[2]
#             w = np.hypot(x2 - x, y2 - y)
#             h = np.hypot(x3 - x2, y3 - y2)
#
#             angle = np.rad2deg(np.arctan2(y2 - y, x2 - x))
#             if angle<=0:
#                 jacquard_angle=-angle
#             else:
#                 jacquard_angle=180-angle
#             rad = np.arctan2(y2 - y, x2 - x)
#             rect_pts = get_rotated_rect(x, y, w, h, angle)
#
#             draw_rect(self.ax, rect_pts, angle, jacquard_angle,self.rect_idx)
#             self.ax.figure.canvas.draw()
#             self.drawn.append((rect_pts, angle))
#
#             cornell_file = os.path.join(self.cornell_dir, f'grasp_{self.rect_idx:03d}.txt')
#             with open(cornell_file, 'w', encoding='utf-8') as f:
#                 for pt in rect_pts:
#                     f.write(f'{pt[0]:.2f} {pt[1]:.2f}\n')
#
#             cx = x + np.cos(rad) * (w / 2)
#             cy = y + np.sin(rad) * (w / 2)
#             self.jacquard_file.write(f'{cx:.2f} {cy:.2f} {jacquard_angle:.5f} {w:.2f} {h:.2f}\n')
#             self.jacquard_file.flush()
#
#             print(f"✅ 保存 grasp {self.rect_idx}")
#             self.rect_idx += 1
#             self.clicks = []
#             for hdl, txt in self.text_handles:
#                 hdl.remove()
#                 txt.remove()
#             self.text_handles.clear()
#
#     def on_scroll(self, event):
#         base_scale = 1.2
#         cur_xlim = self.ax.get_xlim()
#         cur_ylim = self.ax.get_ylim()
#         xdata = event.xdata
#         ydata = event.ydata
#         scale_factor = base_scale if event.button == 'up' else 1 / base_scale
#         new_xlim = [xdata - (xdata - cur_xlim[0]) / scale_factor,
#                     xdata + (cur_xlim[1] - xdata) / scale_factor]
#         new_ylim = [ydata - (ydata - cur_ylim[0]) / scale_factor,
#                     ydata + (cur_ylim[1] - ydata) / scale_factor]
#         self.ax.set_xlim(new_xlim)
#         self.ax.set_ylim(new_ylim)
#         self.ax.figure.canvas.draw()
#
#     def onkey(self, event):
#         if event.key == 'n':
#             self.jacquard_file.close()
#             plt.close(self.fig)
#             self.cur_idx += 1
#             self._run_next_image()
#         elif event.key == 'escape':
#             print("🚫 取消当前 grasp")
#             self.clicks = []
#             for hdl, txt in self.text_handles:
#                 hdl.remove()
#                 txt.remove()
#             self.text_handles.clear()
#             self._redraw_all()
#         elif event.key == 'd':
#             if self.rect_idx > 0:
#                 print(f"🗑️ 删除 grasp {self.rect_idx - 1}")
#                 self.rect_idx -= 1
#                 grasp_file = os.path.join(self.cornell_dir, f'grasp_{self.rect_idx:03d}.txt')
#                 if os.path.exists(grasp_file):
#                     os.remove(grasp_file)
#                 self._truncate_last_line(self.jacquard_path)
#                 if self.drawn:
#                     self.drawn.pop()
#                 self._redraw_all()
#
#     def _truncate_last_line(self, filepath):
#         with open(filepath, 'rb+') as f:
#             f.seek(0, os.SEEK_END)
#             pos = f.tell() - 1
#             while pos > 0 and f.read(1) != b'\n':
#                 pos -= 1
#                 f.seek(pos, os.SEEK_SET)
#             f.truncate(pos + 1)
#
#     def _redraw_all(self):
#         self.ax.clear()
#         self.ax.imshow(self.image)
#         self._update_title()
#         for idx, (pts, angle,jacquard_angle) in enumerate(self.drawn):
#             draw_rect(self.ax, pts, angle, jacquard_angle, idx)
#         self.ax.figure.canvas.draw()
#
# if __name__ == '__main__':
#     img_dir = r"C:\Users\89424\Desktop\grasp_annotate\images"  # 图像文件夹
#     save_dir = r"C:\Users\89424\Desktop\grasp_annotate\annotations"  # 标注保存路径
#     os.makedirs(save_dir, exist_ok=True)
#     AnnotatorUI(img_dir, save_dir)
