"""Step 6 (Phase 3 + 4.5): Auto 9:16 speaker tracking + dynamic zoom / jump-cut feel.

Clip er bhitor frame sample kore face detect kori (OpenCV Haar — bundled), speaker er mukh
onujayi smooth crop trajectory banai. Ekta single ffmpeg `crop` filter string ferot dey
(time-based expression) — single-pass e:
  • mukh follow kore (x track)
  • zoom on hole proti sentence/segment e zoom level alternate kore (jump-cut energy)
Mukh na pele center-crop.
"""
import cv2

AR = 9 / 16  # vertical 9:16


def _even(n):
    n = int(n)
    return n - (n % 2)


def detect_centers(video_path, clip_start, clip_end, sample_fps=3,
                   det_width=640, smooth_win=5):
    """Return (src_w, src_h, crop_w, keyframes[(t_rel, face_center_x)])."""
    cap = cv2.VideoCapture(str(video_path))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720

    crop_w = _even(min(src_w, src_h * AR))
    center_face = src_w / 2.0

    if crop_w >= src_w:                       # portrait/square — horizontal crop l/lagena
        cap.release()
        return src_w, src_h, crop_w, [(0.0, center_face)]

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
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
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            centers.append((x + w / 2.0) / scale)
        else:
            centers.append(None)
    cap.release()

    if not any(c is not None for c in centers):
        return src_w, src_h, crop_w, [(0.0, center_face)]

    # --- anti-shake smoothing chain ---
    filled = _fill_gaps(centers, default=center_face)
    med = _median_filter(filled, 5)            # spike/outlier kill
    sm = _moving_avg(med, max(smooth_win, 7))  # heavy smooth
    # dead-zone + slew: choto noraChora ignore, boro nora dheere follow
    stab = _stabilize(sm, sample_fps, deadzone=28.0, slew_px_s=110.0)
    kf = [(round(i / sample_fps, 2), round(c, 1)) for i, c in enumerate(stab)]
    return src_w, src_h, crop_w, _reduce_keyframes(kf, min_delta=14.0)


def make_crop_filter(video_path, clip_start, clip_end, width, height,
                     sample_fps=3, zoom_amt=0.0, segment_starts=None):
    """Full ffmpeg crop+scale filter string. zoom_amt>0 hole jump-cut zoom on."""
    src_w, src_h, crop_w, kf = detect_centers(
        video_path, clip_start, clip_end, sample_fps=sample_fps)

    fc = _piecewise(kf) if len(kf) > 1 else str(kf[0][1])
    max_x = src_w - crop_w

    if zoom_amt <= 0 or not segment_starts:
        # fixed crop window, sudhu x track
        x = f"min(max(({fc})-{crop_w}/2,0),{max_x})" if max_x > 0 else "0"
        return f"crop={crop_w}:{src_h}:x='{x}':y=0,scale={width}:{height}"

    # --- dynamic zoom (jump-cut): proti segment e zoom level alternate ---
    zf = _zoom_expr(segment_starts, clip_end - clip_start, zoom_amt)
    ch = f"({src_h}/({zf}))"            # crop height (zoom korle choto)
    cw = f"({ch}*{AR})"                 # crop width 9:16
    x = f"min(max(({fc})-({cw})/2,0),{src_w}-({cw}))"
    y = f"(({src_h}-({ch}))/2)"
    return (f"crop=w='{cw}':h='{ch}':x='{x}':y='{y}',"
            f"scale={width}:{height}")


def _zoom_expr(seg_starts, dur, amt):
    """Proti segment alternate kore zoom: even seg = 1.0, odd seg = 1+amt (cut feel)."""
    bounds = sorted(set([0.0] + [s for s in seg_starts if 0 < s < dur]))
    vals = [round(1.0 + (amt if i % 2 else 0.0), 3) for i in range(len(bounds))]
    expr = str(vals[-1])
    for i in range(len(bounds) - 2, -1, -1):
        expr = f"if(lt(t,{round(bounds[i + 1], 2)}),{vals[i]},{expr})"
    return expr


def _piecewise(kf):
    """keyframes [(t,val)] -> piecewise-linear expression of t."""
    expr = str(kf[-1][1])
    for i in range(len(kf) - 2, -1, -1):
        t0, x0 = kf[i]
        t1, x1 = kf[i + 1]
        if t1 == t0:
            continue
        seg = f"({x0}+({round(x1 - x0, 1)})*(t-{t0})/({round(t1 - t0, 2)}))"
        expr = f"if(lt(t,{t1}),{seg},{expr})"
    return expr


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


def _moving_avg(vals, win):
    if win <= 1:
        return vals
    half = win // 2
    return [sum(vals[max(0, i - half):min(len(vals), i + half + 1)])
            / (min(len(vals), i + half + 1) - max(0, i - half))
            for i in range(len(vals))]


def _median_filter(vals, k=5):
    """Spike/outlier (Haar er bhul detection) remove kore."""
    half = k // 2
    out = []
    for i in range(len(vals)):
        win = sorted(vals[max(0, i - half):min(len(vals), i + half + 1)])
        out.append(win[len(win) // 2])
    return out


def _stabilize(vals, fps, deadzone=28.0, slew_px_s=110.0):
    """Held position: choto nora (deadzone er bhitor) hole nara hoy na; boro nora hole
    slew-rate limit kore dheere follow kore — kapakapi/jhakuni dur hoy."""
    if not vals:
        return vals
    step = slew_px_s / max(fps, 1)
    held = vals[0]
    out = [held]
    for v in vals[1:]:
        if abs(v - held) > deadzone:
            d = v - held
            held += max(-step, min(step, d))
        out.append(held)
    return out


def _reduce_keyframes(kf, min_delta=6.0):
    if not kf:
        return kf
    out = [kf[0]]
    for t, x in kf[1:]:
        if abs(x - out[-1][1]) >= min_delta:
            out.append((t, x))
    if out[-1] != kf[-1]:
        out.append(kf[-1])
    return out


# --- backward-compat (older imports) ---
def compute_track(video_path, clip_start, clip_end, target_ar=AR, sample_fps=3):
    src_w, src_h, crop_w, kf = detect_centers(video_path, clip_start, clip_end, sample_fps)
    max_x = src_w - crop_w
    xkf = [(t, round(min(max(c - crop_w / 2, 0), max_x), 1)) for t, c in kf]
    return src_w, src_h, crop_w, xkf


def build_x_expr(keyframes):
    return _piecewise(keyframes) if len(keyframes) > 1 else str(keyframes[0][1])
