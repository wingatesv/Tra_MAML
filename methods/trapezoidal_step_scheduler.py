import math

    
def tra(total_epochs, current_epoch, max_step, min_step, max_step_width):
    step_diff = 0
    # Calculate the midpoint of total_epochs and max_step_width
    epoch_midpoint = total_epochs // 2
    max_step_width_midpoint = max_step_width / 2

    # Calculate the frequency of half max step and the starting and ending epochs of max step frequency
    half_max_step_freq = math.floor(total_epochs * max_step_width_midpoint)
    max_step_freq_start_epoch = epoch_midpoint - half_max_step_freq
    max_step_freq_end_epoch = epoch_midpoint + half_max_step_freq

    # Calculate the size of max step and total step frequency
    max_step_size = max_step_freq_end_epoch - max_step_freq_start_epoch
    total_step_freq_size = total_epochs - max_step_size

    # Calculate the size of half step frequency and the frequency of step
    half_step_freq_size = total_step_freq_size // 2
    step_freq = math.floor(half_step_freq_size / (max_step - 1))

    # Calculate the total step frequency and adjust max step size if necessary
    total_step_freq = (max_step - 1) * step_freq * 2
    if total_step_freq < (total_epochs - max_step_size):
        step_diff = total_epochs - total_step_freq - max_step_size
        max_step_size = max_step_size + step_diff if max_step_width != 0 else max_step_size

    # Calculate the new half step frequency size
    new_half_step_freq_size = total_step_freq // 2

    if max_step_width == 0 and step_diff > 0:
         # Determine the current step based on the current epoch
        if current_epoch < new_half_step_freq_size:
            current_step = min_step + current_epoch // step_freq
        elif current_epoch < (new_half_step_freq_size + step_diff):
            current_step = (max_step - 1)
        else:
            current_step = (max_step - 1) - (current_epoch - step_freq * (max_step - 1) - step_diff) // step_freq       
    else:
        # Determine the current step based on the current epoch
        if current_epoch < new_half_step_freq_size:
            current_step = min_step + current_epoch // step_freq
        elif current_epoch < (new_half_step_freq_size + max_step_size):
            current_step = max_step
        else:
            current_step = (max_step - 1) - (current_epoch - step_freq * (max_step - 1) - max_step_size) // step_freq

    return current_step
