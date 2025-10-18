from PIL import Image
import glob
import sys

if len(sys.argv) != 3:
    print("usage: png2gif.py <glob> <gif_filename>")

print(sys.argv)
print(glob.glob(sys.argv[1]))

# Create the frames
frames = []
imgs = sorted(glob.glob(sys.argv[1]))
for i in imgs:
    new_frame = Image.open(i)
    frames.append(new_frame)

# Save into a GIF file that loops forever
frames[0].copy().save(sys.argv[2], format='GIF', append_images=frames[1:], save_all=True, duration=100, loop=0, disposal=2)
