#!/usr/bin/env python3
"""Test script to verify LTR329 works with Adafruit library through multiplexer."""

import time
import board
import busio
import adafruit_pca9548a
import adafruit_ltr329_ltr303

def test_ltr329_direct():
    """Test LTR329 directly on main I2C bus."""
    print("Testing LTR329 on direct I2C bus...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ltr = adafruit_ltr329_ltr303.LTR329(i2c, address=0x29)
        print(f"✓ LTR329 initialized at 0x29")
        
        # Test reading
        vis_ir = ltr.visible_plus_ir_light
        ir = ltr.ir_light
        print(f"  Visible+IR: {vis_ir}")
        print(f"  IR: {ir}")
        return True
    except Exception as e:
        print(f"✗ Direct I2C failed: {e}")
        return False

def test_ltr329_via_multiplexer():
    """Test LTR329 through PCA9548 multiplexer."""
    print("\nTesting LTR329 via multiplexer...")
    try:
        # Initialize I2C and multiplexer
        i2c = busio.I2C(board.SCL, board.SDA)
        pca = adafruit_pca9548a.PCA9548A(i2c, address=0x70)
        
        # Test channel 0 (where LTR329 should be)
        print("Trying multiplexer channel 0...")
        channel = pca[0]
        ltr = adafruit_ltr329_ltr303.LTR329(channel, address=0x29)
        print(f"✓ LTR329 initialized via multiplexer channel 0")
        
        # Test reading
        vis_ir = ltr.visible_plus_ir_light
        ir = ltr.ir_light
        print(f"  Visible+IR: {vis_ir}")
        print(f"  IR: {ir}")
        return True
    except Exception as e:
        print(f"✗ Multiplexer access failed: {e}")
        return False

def scan_multiplexer_channels():
    """Scan all multiplexer channels for LTR329."""
    print("\nScanning multiplexer channels for LTR329...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        pca = adafruit_pca9548a.PCA9548A(i2c, address=0x70)
        
        for channel_num in range(8):
            try:
                print(f"  Channel {channel_num}:", end=" ")
                channel = pca[channel_num]
                ltr = adafruit_ltr329_ltr303.LTR329(channel, address=0x29)
                vis_ir = ltr.visible_plus_ir_light
                print(f"✓ LTR329 found! Visible+IR={vis_ir}")
                return channel_num
            except Exception as e:
                print(f"✗ {type(e).__name__}")
        
        print("LTR329 not found on any multiplexer channel")
        return None
    except Exception as e:
        print(f"✗ Multiplexer scan failed: {e}")
        return None

if __name__ == "__main__":
    print("LTR329 Hardware Test")
    print("=" * 30)
    
    # Test direct connection first
    direct_works = test_ltr329_direct()
    
    # Test via multiplexer
    mux_works = test_ltr329_via_multiplexer()
    
    # If neither worked, scan all channels
    if not direct_works and not mux_works:
        found_channel = scan_multiplexer_channels()
        if found_channel is not None:
            print(f"\n✓ LTR329 found on multiplexer channel {found_channel}")
    
    print("\nTest complete.")