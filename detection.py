def detect_anomaly(v_dc, freq, current, prev_freq, dt, rocof_thresh=1.0):

    # ROCOF hesapla
    rocof = abs(freq - prev_freq) / dt
    if rocof > rocof_thresh:
        return "ROCOF_FAULT"

    # DC Bus kontrolü (570-630V)
    if v_dc < 570 or v_dc > 630:
        return "DC_VOLTAGE_FAULT"

    # Frekans kontrolü (49-51 Hz)
    if freq < 49 or freq > 51:
        return "FREQUENCY_FAULT"

    # Akım (%10 sapma varsayımı)
    if current > 11 or current < 9:
        return "OVERCURRENT_FAULT"

    return None