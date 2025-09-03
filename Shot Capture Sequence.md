# Shot Capture Sequence

## Setup
The following is 1 string, 1 athlete, making 5 shots with no misses on 5 different targets setup in what is called a stage. Stage configurations are different in setup between the number of targets (usually 5 or 6), their height, distance, size, shape. An athlete could miss a target meaning a shot taken and captured by the timer but not detected by the sensor. An athlete could shoot twice and impact the same target twice as well.

## Sequence

0. Timer and Sensor are on and connected and validated; reporting it to log with device ids confirmed

1. To begin a String the RO says "Shooter ready"

2. RO says "Standby" and presses the Timer start button; I would like to report that the button was pressed

3. Timer starts a random number between 1-3 seconds that counts down to 0, I would like to capture and report this random number

4. Upon 0 the Timer will beep significant to the athlete to start, I think this is T0 and capture and report this string_start_time

5. Athlete begins by moving from start cone to first target and fires first shot about .45s after T0 which registers on the Timer as string_shot_1 with a time and split_time from T0

6. As athlete moves to the next target, the BT50 sensor attached to target_1 detects an impact approx .11s as string_impact_1 and reports time, split_time, sensor telemetry data and makes a judgement of Impact made based on threshold. An enhancement here will be to judge based on variables like target plate size, distance, caliber and more if the impact was Impact, Edge_Impact or Miss_Near, though we could also define things like interference.

7. Athlete engages the next target and calls a shot, fires second shot about .25s after string_shot_1 which registers on the Timer as string_shot_2 with a time and split_time from string_shot_1 and T0

8. As athlete moves to the next target, the BT50 sensor attached to target_2 detects an impact approx .18s as string_impact_2 from string_shot_2 and reports time, split_time, sensor telemetry data and makes a judgement of Impact.

9. Athlete engages the next target and calls a shot, fires next shot about .12s after string_shot_2 which registers on the Timer as string_shot_3 with a time and split_time from string_shot_2 and T0

10. As athlete moves to the next target, the BT50 sensor attached to target_3 detects an impact approx .08s as string_impact_3 from string_shot_3 and reports time, split_time, sensor telemetry data and makes a judgement of Impact.

11. Athlete engages the next target and calls a shot, fires next shot about .11s after string_shot_3 which registers on the Timer as string_shot_4 with a time and split_time from string_shot_3 and T0

12. As athlete moves to the next target, the BT50 sensor attached to target_4 detects an impact approx .14s as string_impact_4 from string_shot_4 and reports time, split_time, sensor telemetry data and makes a judgement of Impact.

13. Athlete engages the next target and calls a shot, fires next shot about .14s after string_shot_4 which registers on the Timer as string_shot_5 with a time and split_time from string_shot_4 and T0

14. As athlete moves to the next target, the BT50 sensor attached to target_5 detects an impact approx .18s as string_impact_5 from string_shot_5 and reports time, split_time, sensor telemetry data and makes a judgement of Impact.

15. RO will then confirm that the athlete has engaged and hit all targets in valid order and press the arrow button on AMG timer to signify a stop which ends the String.

16. Timer then reports a summary of the string with various data points.

## Key Requirement
The above sequence shows that we need to capture and report data within the sample file where the telemetry data from the BT50 could identify multiple impacts within .08 seconds of each other on a target.