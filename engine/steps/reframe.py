"""Step 6: Auto 9:16 speaker reframe — YuNet face detect + stable framing + smooth zoom.

Fix gula:
  • Detection: purono Haar er bodole **YuNet** (onek accurate) — mukh thik dhore, tai
    subject center e thake (side e jay na). YuNet na pele Haar fallback.
  • Framing: heavy smoothing (median + avg + dead-zone + slew) — kapakapi nai.
  • Zoom: smooth sine breathing (start/ses e normal, majhe subtle zoom) — hard jump nai.
Ekta single ffmpeg crop+scale filter string ferot dey (time-based)।
"""
from pathlib import Path

import cv2

AR = 9 / 16
ENGINE_DIR = Path(__file__).resolve().parent.parent
YUNET_PATH = ENGINE_DIR / "assets" / "face_yunet.onnx"

_YUNET = None
_HAAR = None


def _even(n):
    n = int(n)
    return n - (n % 2)


def _get_yunet():
    global _YUNET
    if _YUNET is None:
        if YUNET_PATH.exists() and hasattr(cv2, "FaceDetectorYN"):
            try:
                _YUNET = cv2.FaceDetectorYN.create(
                    str(YUNET_PATH), "", (320, 320), 0.6, 0.3, 5000)
            except Exception:
                _YUNET = False
        else:
            _YUNET = False
    return _YUNET or None


def _get_haar():
    global _HAAR
    if _HAAR is None:
        try:
            _HAAR = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        except Exception:
            _HAAR = False
    return _HAAR or None


def _detect_face_x(frame):
    """Frame theke sobcheye boro mukh er center-x (frame coords), na pele None."""
    h, w = frame.shape[:2]
    yn = _get_yunet()
    if yn is not None:
        try:
            yn.setInputSize((w, h))
            _, faces = yn.detect(frame)
        except Exception:
            faces = None
        if faces is not None and len(faces):
            f = max(faces, key=lambda r: r[2] * r[3])   # boro mukh
            return float(f[0] + f[2] / 2.0)
        return None
    haar = _get_haar()
    if haar is None:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = haar.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
    if len(faces):
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        return float(x + fw / 2.0)
    return None


def _sample_centers(video_path, clip_start, clip_end, sample_fps, det_width=480):
    cap = cv2.VideoCapture(str(video_path))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if not (1 <= src_fps <= 120):
        src_fps = 30.0
    scale = det_width / src_w if src_w > det_width else 1.0
    dur = max(clip_end - clip_start, 0.1)
    n = max(int(dur * sample_fps), 1)
    centers = []
    for i in range(n + 1):
        tr = i / sample_fps
        cap.set(cv2.CAP_PROP_POS_MSEC, (clip_start + tr) * 1000.0)
        ok, frame = cap.read()
        if not ok:
            centers.append(None)
            continue
        small = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame
        cx = _detect_face_x(small)
        centers.append(cx / scale if cx is not None else None)
    cap.release()
    return src_w, src_h, src_fps, centers


def _probe_dims(video_path):
    cap = cv2.VideoCapture(str(video_path))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    if not (1 <= src_fps <= 120):
        src_fps = 30.0
    return src_w, src_h, src_fps


def make_crop_filter(video_path, clip_start, clip_end, width, height,
                     sample_fps=3, zoom_amt=0.0, segment_starts=None, track=True):
    """9:16 crop+scale filter string — face-centered (track=True) + smooth zoom."""
    if track:
        src_w, src_h, src_fps, centers = _sample_centers(
            video_path, clip_start, clip_end, sample_fps)
    else:
        src_w, src_h, src_fps = _probe_dims(video_path)
        centers = []          # tracking off — center crop, kintu zoom thakbe
    crop_w = _even(min(src_w, src_h * AR))
    center_x = src_w / 2.0

    # face-center trajectory (stable)
    if any(c is not None for c in centers):
        filled = _fill_gaps(centers, center_x)
        med = _median_filter(filled, 5)
        sm = _moving_avg(med, 9)
        stab = _stabilize(sm, sample_fps, deadzone=25.0, slew_px_s=140.0)
        kf = _reduce([(round(i / sample_fps, 2), round(v, 1)) for i, v in enumerate(stab)])
        fc = _piecewise(kf)
    else:
        fc = str(round(center_x, 1))   # mukh na pele center

    dur = max(clip_end - clip_start, 0.1)

    # face-tracked 9:16 crop (fixed size; x per-frame pan valid). Mukh na dhorle center.
    max_x = src_w - crop_w
    if max_x <= 0:
        base = f"crop={crop_w}:{src_h}:x=0:y=0,scale={width}:{height}"
    else:
        x = f"min(max(({fc})-{crop_w}/2,0),{max_x})"
        base = f"crop={crop_w}:{src_h}:x='{x}':y=0,scale={width}:{height}"

    if not (zoom_amt and zoom_amt > 0):
        return base

    # smooth zoom: zoompan (crop-size t diye animate hoy na, tai eta lagbe).
    # sine breathing — start/ses normal, majhe zoom. jhakuni nai.
    n = max(int(round(dur * src_fps)), 2)
    z = f"1+{round(zoom_amt, 3)}*sin(PI*on/{n})"
    zp = (f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':"
          f"d=1:s={width}x{height}:fps={round(src_fps, 3)}")
    return f"{base},{zp}"


# ---------- smoothing helpers ----------

def _fill_gaps(vals, default):
    out = list(vals)
    last = None
    for i, v in enumerate(out):
        if v is None:
            out[i] = last
        else:
            last = v
    nxt = None
    for i in range(len(out) - 1, -1, -1):
        if out[i] is None:
            out[i] = nxt if nxt is not None else default
        else:
            nxt = out[i]
    return out


def _median_filter(vals, k=5):
    half = k // 2
    out = []
    for i in range(len(vals)):
        win = sorted(vals[max(0, i - half):min(len(vals), i + half + 1)])
        out.append(win[len(win) // 2])
    return out


def _moving_avg(vals, win):
    if win <= 1:
        return vals
    half = win // 2
    return [sum(vals[max(0, i - half):min(len(vals), i + half + 1)])
            / (min(len(vals), i + half + 1) - max(0, i - half))
            for i in range(len(vals))]


def _stabilize(vals, fps, deadzone=25.0, slew_px_s=140.0):
    if not vals:
        return vals
    step = slew_px_s / max(fps, 1)
    held = vals[0]
    out = [held]
    for v in vals[1:]:
        if abs(v - held) > deadzone:
            held += max(-step, min(step, v - held))
        out.append(held)
    return out


def _reduce(kf, min_delta=10.0):
    if not kf:
        return kf
    out = [kf[0]]
    for t, x in kf[1:]:
        if abs(x - out[-1][1]) >= min_delta:
            out.append((t, x))
    if out[-1] != kf[-1]:
        out.append(kf[-1])
    return out


def _piecewise(kf):
    if len(kf) == 1:
        return str(kf[0][1])
    expr = str(kf[-1][1])
    for i in range(len(kf) - 2, -1, -1):
        t0, x0 = kf[i]
        t1, x1 = kf[i + 1]
        if t1 == t0:
            continue
        seg = f"({x0}+({round(x1 - x0, 1)})*(t-{t0})/({round(t1 - t0, 2)}))"
        expr = f"if(lt(t,{t1}),{seg},{expr})"
    return expr
