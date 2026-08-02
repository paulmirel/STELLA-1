# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
VCNL4030 Full Test

Full configuration and reading example for VCNL4030X01
proximity and ambient light sensor.

Displays all configuration settings with human-readable names,
then continuously prints sensor readings.
"""

import time

import board

from adafruit_vcnl4030 import (
    VCNL4030,
    VCNL4030_ALS_IF_H,
    VCNL4030_ALS_IF_L,
    VCNL4030_PROX_IF_AWAY,
    VCNL4030_PROX_IF_CLOSE,
    VCNL4030_PROX_SPFLAG,
    ALSIntegrationTime,
    ALSPersistence,
    ProxDuty,
    ProxGain,
    ProxIntegrationTime,
    ProxInterruptMode,
    ProxLEDCurrent,
    ProxPersistence,
    SunlightCancelCurrent,
)

print("VCNL4030 Full Test")
print("==================")

sensor = VCNL4030(board.I2C())
print("VCNL4030 Found!")

# === ALS Configuration ===
print("\n--- ALS Configuration ---")

sensor.als_enabled = True
print(f"ALS Enabled: {'Yes' if sensor.als_enabled else 'No'}")

sensor.white_channel_enabled = True
print(f"White Channel: {'Enabled' if sensor.white_channel_enabled else 'Disabled'}")

sensor.als_integration_time = ALSIntegrationTime.MS_100
it_names = {
    ALSIntegrationTime.MS_50: "50ms",
    ALSIntegrationTime.MS_100: "100ms",
    ALSIntegrationTime.MS_200: "200ms",
    ALSIntegrationTime.MS_400: "400ms",
    ALSIntegrationTime.MS_800: "800ms",
}
print(f"Integration Time: {it_names.get(sensor.als_integration_time, 'Unknown')}")

sensor.als_persistence = ALSPersistence.CYCLES_1
pers_names = {
    ALSPersistence.CYCLES_1: "1 sample",
    ALSPersistence.CYCLES_2: "2 samples",
    ALSPersistence.CYCLES_4: "4 samples",
    ALSPersistence.CYCLES_8: "8 samples",
}
print(f"Persistence: {pers_names.get(sensor.als_persistence, 'Unknown')}")

sensor.als_high_dynamic_range = False
print(f"High Dynamic Range: {'Yes (2x range)' if sensor.als_high_dynamic_range else 'No (normal)'}")

sensor.als_low_sensitivity = False
print(f"Low Sensitivity (NS): {'Yes (2x range)' if sensor.als_low_sensitivity else 'No (normal)'}")

sensor.als_interrupt_enabled = False
print(f"Interrupt: {'Enabled' if sensor.als_interrupt_enabled else 'Disabled'}")

# === Proximity Configuration ===
print("\n--- Proximity Configuration ---")

sensor.proximity_enabled = True
print(f"Prox Enabled: {'Yes' if sensor.proximity_enabled else 'No'}")

sensor.led_current = ProxLEDCurrent.MA_100
led_names = {
    ProxLEDCurrent.MA_50: "50mA",
    ProxLEDCurrent.MA_75: "75mA",
    ProxLEDCurrent.MA_100: "100mA",
    ProxLEDCurrent.MA_120: "120mA",
    ProxLEDCurrent.MA_140: "140mA",
    ProxLEDCurrent.MA_160: "160mA",
    ProxLEDCurrent.MA_180: "180mA",
    ProxLEDCurrent.MA_200: "200mA",
}
print(f"LED Current: {led_names.get(sensor.led_current, 'Unknown')}")

sensor.proximity_duty = ProxDuty.RATIO_160
duty_names = {
    ProxDuty.RATIO_40: "1/40",
    ProxDuty.RATIO_80: "1/80",
    ProxDuty.RATIO_160: "1/160",
    ProxDuty.RATIO_320: "1/320",
}
print(f"Duty Cycle: {duty_names.get(sensor.proximity_duty, 'Unknown')}")

sensor.proximity_integration_time = ProxIntegrationTime.T_4
prox_it_names = {
    ProxIntegrationTime.T_1: "1T",
    ProxIntegrationTime.T_1_5: "1.5T",
    ProxIntegrationTime.T_2: "2T",
    ProxIntegrationTime.T_2_5: "2.5T",
    ProxIntegrationTime.T_3: "3T",
    ProxIntegrationTime.T_3_5: "3.5T",
    ProxIntegrationTime.T_4: "4T",
    ProxIntegrationTime.T_8: "8T",
}
print(f"Integration Time: {prox_it_names.get(sensor.proximity_integration_time, 'Unknown')}")

sensor.proximity_gain = ProxGain.TWO_STEP
gain_names = {
    ProxGain.TWO_STEP: "Two-step (most sensitive)",
    ProxGain.SINGLE_8X: "Single 8x range (least sensitive)",
    ProxGain.SINGLE_1X: "Single 1x range",
}
print(f"Gain: {gain_names.get(sensor.proximity_gain, 'Unknown')}")

sensor.proximity_persistence = ProxPersistence.CYCLES_1
prox_pers_names = {
    ProxPersistence.CYCLES_1: "1 sample",
    ProxPersistence.CYCLES_2: "2 samples",
    ProxPersistence.CYCLES_3: "3 samples",
    ProxPersistence.CYCLES_4: "4 samples",
}
print(f"Persistence: {prox_pers_names.get(sensor.proximity_persistence, 'Unknown')}")

sensor.proximity_interrupt_mode = ProxInterruptMode.DISABLED
int_mode_names = {
    ProxInterruptMode.DISABLED: "Disabled",
    ProxInterruptMode.CLOSE: "Close only",
    ProxInterruptMode.AWAY: "Away only",
    ProxInterruptMode.BOTH: "Close and Away",
}
print(f"Interrupt Mode: {int_mode_names.get(sensor.proximity_interrupt_mode, 'Unknown')}")

sensor.proximity_resolution_16bit = True
print(f"Resolution: {'16-bit' if sensor.proximity_resolution_16bit else '12-bit'}")

sensor.proximity_low_sensitivity = False
print(f"Low Sensitivity: {'Yes' if sensor.proximity_low_sensitivity else 'No'}")

sensor.proximity_smart_persistence = False
print(f"Smart Persistence: {'Enabled' if sensor.proximity_smart_persistence else 'Disabled'}")

sensor.proximity_active_force_mode = False
print(f"Active Force: {'Enabled' if sensor.proximity_active_force_mode else 'Disabled'}")

sensor.proximity_logic_mode = False
print(f"Logic Output Mode: {'Enabled' if sensor.proximity_logic_mode else 'Disabled'}")

# === Sunlight Cancellation ===
print("\n--- Sunlight Cancellation ---")

sensor.sunlight_cancellation_enabled = False
print(f"SC Enabled: {'Yes' if sensor.sunlight_cancellation_enabled else 'No'}")

sensor.sunlight_cancel_current = SunlightCancelCurrent.X1
sc_cur_names = {
    SunlightCancelCurrent.X1: "1x",
    SunlightCancelCurrent.X2: "2x",
    SunlightCancelCurrent.X4: "4x",
    SunlightCancelCurrent.X8: "8x",
}
print(f"SC Current: {sc_cur_names.get(sensor.sunlight_cancel_current, 'Unknown')}")

sensor.proximity_cancellation = 0
print(f"Cancellation Level: {sensor.proximity_cancellation}")

# === Start continuous reading ===
print("\n--- Sensor Readings ---\n")

time.sleep(0.2)  # Let sensors stabilize

while True:
    flags = sensor.interrupt_flags
    flag_str = ""
    if flags:
        parts = []
        if flags & VCNL4030_PROX_IF_CLOSE:
            parts.append("CLOSE")
        if flags & VCNL4030_PROX_IF_AWAY:
            parts.append("AWAY")
        if flags & VCNL4030_ALS_IF_H:
            parts.append("ALS_HI")
        if flags & VCNL4030_ALS_IF_L:
            parts.append("ALS_LO")
        if flags & VCNL4030_PROX_SPFLAG:
            parts.append("SUNPROT")
        flag_str = "\tFlags: " + " ".join(parts)

    print(
        f"Prox: {sensor.proximity}\tALS: {sensor.als}"
        + f"\tLux: {sensor.lux:.2f}\tWhite: {sensor.white}{flag_str}"
    )
    time.sleep(0.1)
