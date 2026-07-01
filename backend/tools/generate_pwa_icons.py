import os
from PIL import Image, ImageDraw, ImageFilter

def generate_icons():
    # Base path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    public_dir = os.path.join(base_dir, "frontend", "public")
    os.makedirs(public_dir, exist_ok=True)

    # 1. Create a 512x512 master icon
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw a premium rounded background card
    margin = 20
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=90,
        fill=(9, 13, 22, 255) # Deep Slate #090D16
    )

    # Draw a glowing center gradient circle
    glow_size = 280
    glow_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    
    # Draw concentric circles to simulate a radial gradient glow
    center = size // 2
    for r in range(glow_size, 0, -4):
        alpha = int(80 * (1 - r / glow_size))
        # Gradient from Indigo (79, 70, 229) to Cyan (6, 182, 212)
        ratio = r / glow_size
        red = int(79 * (1 - ratio) + 6 * ratio)
        green = int(70 * (1 - ratio) + 182 * ratio)
        blue = int(229 * (1 - ratio) + 212 * ratio)
        
        glow_draw.ellipse(
            [center - r, center - r, center + r, center + r],
            fill=(red, green, blue, alpha)
        )
    
    # Apply a slight blur to the glow for smooth ambient depth
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(glow_img)

    # Draw a futuristic DevOps infinity symbol/loop in the center
    symbol_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sym_draw = ImageDraw.Draw(symbol_img)
    
    # Draw two overlapping circles to make the infinity shape
    cx1, cy1 = center - 60, center
    cx2, cy2 = center + 60, center
    r_sym = 85
    thickness = 28
    
    # Draw left loop
    sym_draw.ellipse([cx1 - r_sym, cy1 - r_sym, cx1 + r_sym, cy1 + r_sym], outline=(255, 255, 255, 255), width=thickness)
    # Draw right loop
    sym_draw.ellipse([cx2 - r_sym, cy2 - r_sym, cx2 + r_sym, cy2 + r_sym], outline=(255, 255, 255, 255), width=thickness)
    
    # Draw center connecting nodes/glowing dots
    dot_r = 18
    sym_draw.ellipse([center - dot_r, center - dot_r, center + dot_r, center + dot_r], fill=(6, 182, 212, 255))
    
    # Apply a subtle drop shadow to the symbol
    shadow = symbol_img.filter(ImageFilter.GaussianBlur(4))
    shadow_offset = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_offset_draw = ImageDraw.Draw(shadow_offset)
    shadow_offset.alpha_composite(shadow, (0, 6)) # Shift down slightly
    
    # Composite shadow and symbol
    img.alpha_composite(shadow_offset)
    img.alpha_composite(symbol_img)

    # Save the 512x512 icon
    icon512_path = os.path.join(public_dir, "icon-512.png")
    img.save(icon512_path, "PNG")
    print(f"Generated 512x512 PWA Icon: {icon512_path}")

    # Resize and save the 192x192 icon
    img_192 = img.resize((192, 192), Image.Resampling.LANCZOS)
    icon192_path = os.path.join(public_dir, "icon-192.png")
    img_192.save(icon192_path, "PNG")
    print(f"Generated 192x192 PWA Icon: {icon192_path}")

if __name__ == "__main__":
    generate_icons()
