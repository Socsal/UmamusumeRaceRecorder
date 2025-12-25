import sys
import os
import shutil
"""
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_01.png" 120 120 item_01.png
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_02.png" 120 120 item_02.png
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_03.png" 120 120 item_03.png
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_04.png" 120 120 item_04.png
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_05.png" 120 120 item_05.png
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_06.png" 120 120 item_06.png
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_07.png" 120 120 item_07.png
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_08.png" 120 120 item_08.png
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_09.png" 120 120 item_09.png
python test.py "D:\Code\python\UmamusumeRaceRecorder\assets\templates\item_10.png" 120 120 item_10.png

"""

def resize_with_pillow(src_path, dst_path, w, h):
    from PIL import Image
    im = Image.open(src_path)
    im = im.convert('RGBA')
    im = im.resize((w, h), Image.LANCZOS)
    im.save(dst_path, format='PNG')

def resize_with_cv2(src_path, dst_path, w, h):
    import cv2
    im = cv2.imdecode(np.fromfile(src_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if im is None:
        raise RuntimeError('cv2 cannot read image')
    im = cv2.resize(im, (w, h), interpolation=cv2.INTER_LANCZOS4)
    # use imwrite with unicode path on Windows
    ext = os.path.splitext(dst_path)[1].lower()
    if ext == '.png':
        cv2.imencode('.png', im)[1].tofile(dst_path)
    else:
        cv2.imencode(ext or '.png', im)[1].tofile(dst_path)

def main(argv):
    if len(argv) < 4:
        print('用法: python test.py <input.png> <width> <height> [output.png]')
        return 1
    src = argv[1]
    try:
        w = int(argv[2])
        h = int(argv[3])
    except Exception:
        print('宽高必须为整数')
        return 1
    dst = argv[4] if len(argv) >= 5 else src

    if not os.path.isfile(src):
        print('输入文件不存在:', src)
        return 1

    # 如果输出是覆盖输入，先备份
    overwrite = os.path.abspath(src) == os.path.abspath(dst)
    if overwrite:
        bak = src + '.bak'
        shutil.copy2(src, bak)

    # 尝试使用 Pillow
    try:
        resize_with_pillow(src, dst, w, h)
        print('已保存', dst)
        return 0
    except Exception:
        pass

    # 回退到 OpenCV（需 numpy, opencv-python）
    try:
        import numpy as np  # noqa: F401
        resize_with_cv2(src, dst, w, h)
        print('已保存', dst)
        return 0
    except Exception as e:
        print('缩放失败，请安装 Pillow: pip install pillow 或 opencv-python numpy')
        print('错误详情:', e)
        # 若备份存在但目标覆盖失败，尝试还原
        if overwrite and os.path.exists(bak):
            try:
                shutil.move(bak, src)
            except Exception:
                pass
        return 2

if __name__ == '__main__':
    sys.exit(main(sys.argv))
