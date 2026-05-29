# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_midi_parser`
================================================================================

CircuitPython helper for parsing MIDI files

This library provides classes for parsing and playing Standard MIDI Files (SMF) in CircuitPython.
It supports Format 0 (single track) and Format 1 (multiple tracks) MIDI files, and provides
a flexible playback system that can be extended for custom MIDI applications.

* Author(s): Liz Clark

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
"""

try:
    from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union
except ImportError:
    pass
import time

__version__ = "1.2.1"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_MIDI_Parser.git"


class MIDIParseError(Exception):
    """Exception raised when there's an error parsing a MIDI file."""

    pass


class MIDIParser:
    """
    Class for parsing and playing Standard MIDI files.
    Supports Format 0 (single track) and Format 1 (multiple tracks) MIDI files.

    :param str filename: Path to the MIDI file
    """

    def __init__(self) -> None:
        """
        Initialize the MIDI parser.

        :param str filename: Path to the MIDI file
        """
        self._filename: Optional[str] = None
        self._events: List[Dict[str, Any]] = []
        self._tempo: int = 500000  # Default tempo (microseconds per quarter note)
        self._ticks_per_beat: int = 480  # Default time division
        self._current_event_index: int = 0
        self._format_type: int = 0
        self._num_tracks: int = 0
        self._parsed: bool = False
        self._last_absolute_time: int = 0

    @property
    def filename(self) -> str:
        """The filename of the MIDI file being parsed."""
        return self._filename

    @property
    def events(self) -> List[Dict[str, Any]]:
        """List of all MIDI events in the file, sorted by absolute time."""
        return self._events

    @property
    def tempo(self) -> int:
        """
        Current tempo in microseconds per quarter note.
        Default is 500,000 (120 BPM).
        """
        return self._tempo

    @property
    def ticks_per_beat(self) -> int:
        """
        Number of ticks per quarter note (time division) from the MIDI file.
        """
        return self._ticks_per_beat

    @property
    def format_type(self) -> int:
        """
        MIDI file format type (0, 1, or 2).
        0 = single track, 1 = multiple tracks, 2 = multiple songs
        """
        return self._format_type

    @property
    def num_tracks(self) -> int:
        """Number of tracks in the MIDI file."""
        return self._num_tracks

    @property
    def parsed(self) -> bool:
        """Whether the MIDI file has been successfully parsed."""
        return self._parsed

    @property
    def current_event_index(self) -> int:
        """Index of the next event to be played."""
        return self._current_event_index

    @property
    def current_event(self) -> Optional[Dict[str, Any]]:
        """
        The current event to be played, or None if at the end.
        Does not advance the event index.

        :return: A dictionary containing event data or None if at the end of events
        :rtype: Optional[Dict[str, Any]]
        """
        if self._current_event_index < len(self._events):
            return self._events[self._current_event_index]
        return None

    @property
    def next_event(self) -> Optional[Dict[str, Any]]:
        """
        The next event to be played, or None if at the end.
        Advances the event index.

        :return: A dictionary containing event data or None if at the end of events
        :rtype: Optional[Dict[str, Any]]
        """
        event = self.current_event
        if event:
            self._current_event_index += 1
        return event

    @property
    def more_events(self) -> bool:
        """Whether there are more events to be played."""
        return self._current_event_index < len(self._events)

    @property
    def bpm(self) -> float:
        """
        Current tempo in beats per minute (BPM).

        :return: The current BPM calculated from the tempo
        :rtype: float
        """
        return 60000000 / self._tempo

    @property
    def note_count(self) -> int:
        """
        Number of note-on events in the MIDI file.

        :return: Count of note-on events
        :rtype: int
        """
        return sum(1 for e in self._events if e["type"] == "note_on")

    @staticmethod
    def _read_variable_length(data: bytes, offset: int) -> Tuple[int, int]:
        """
        Read a variable length quantity from the data starting at offset.

        :param bytes data: MIDI file data
        :param int offset: Current offset into the data
        :return: A tuple containing (value, new_offset)
        :rtype: Tuple[int, int]
        :raises MIDIParseError: If the variable length value is invalid or extends beyond the data
        """
        value = 0
        byte_count = 0
        while byte_count < 4:  # Prevent infinite loop
            if offset >= len(data):
                raise MIDIParseError(
                    f"Variable length value extends beyond data at offset {offset}"
                )
            byte = data[offset]
            offset += 1
            value = (value << 7) | (byte & 0x7F)
            byte_count += 1
            if not (byte & 0x80):
                break
        return value, offset

    def clear(self) -> None:
        """
        Clear all parsed data and reset the parser state.
        """
        self._filename = None
        self._events = []
        self._tempo = 500000  # Default tempo
        self._ticks_per_beat = 480  # Default division
        self._current_event_index = 0
        self._format_type = 0
        self._num_tracks = 0
        self._parsed = False
        self._last_absolute_time = 0

    def parse(self, filename: str, debug: bool = False) -> bool:  # noqa: PLR0912 PLR0915 PLR0914
        """
        Parse the MIDI file and extract events.

        :param bool debug: Whether to print detailed parsing information
        :return: True if parsing was successful
        :rtype: bool
        :raises MIDIParseError: If the file doesn't exist or is not a valid MIDI file
        """
        self.clear()
        self._filename = filename
        try:  # noqa: PLR1702
            with open(self._filename, "rb") as file:
                data = file.read()
            if len(data) < 14:
                raise MIDIParseError("File too short to be a valid MIDI file")
            if data[0:4] != b"MThd":
                raise MIDIParseError("Not a valid MIDI file - missing MThd header")
            # header_length = (data[4] << 24) | (data[5] << 16) | (data[6] << 8) | data[7]
            self._format_type = (data[8] << 8) | data[9]
            self._num_tracks = (data[10] << 8) | data[11]
            self._ticks_per_beat = (data[12] << 8) | data[13]
            if debug:
                print(
                    f"Format: {self._format_type}, Tracks: {self._num_tracks},"
                    + f"Ticks per beat: {self._ticks_per_beat}"
                )
            offset = 14
            for track_num in range(self._num_tracks):
                if debug:
                    print(f"Parsing track {track_num + 1}")
                if offset + 8 > len(data):
                    raise MIDIParseError(
                        f"Unexpected end of file while reading track {track_num + 1}"
                    )
                if data[offset : offset + 4] != b"MTrk":
                    if debug:
                        print(f"Track {track_num + 1} chunk not found at offset {offset}")
                    next_track = data.find(b"MTrk", offset)
                    if next_track >= 0:
                        offset = next_track
                    else:
                        raise MIDIParseError(f"Could not find track {track_num + 1}")
                track_length = (
                    (data[offset + 4] << 24)
                    | (data[offset + 5] << 16)
                    | (data[offset + 6] << 8)
                    | data[offset + 7]
                )
                if debug:
                    print(f"Track length: {track_length} bytes")
                track_start = offset + 8
                track_end = track_start + track_length
                if track_end > len(data):
                    raise MIDIParseError(
                        f"Track {track_num + 1} extends beyond file end: {track_end} > {len(data)}"
                    )
                offset = track_start
                absolute_time = 0
                last_status = 0
                while offset < track_end:
                    delta_time, offset = self._read_variable_length(data, offset)
                    absolute_time += delta_time
                    if offset >= len(data):
                        raise MIDIParseError(f"Reached end of file unexpectedly at offset {offset}")
                    if data[offset] & 0x80:
                        status = data[offset]
                        offset += 1
                        last_status = status
                    else:
                        status = last_status
                    if offset >= len(data):
                        raise MIDIParseError(
                            f"Reached end of file after status byte at offset {offset}"
                        )
                    event_type = status & 0xF0
                    channel = status & 0x0F
                    if event_type == 0x80:
                        if offset + 1 >= len(data):
                            raise MIDIParseError(f"Incomplete Note Off event at offset {offset}")
                        note = data[offset]
                        velocity = data[offset + 1]
                        offset += 2
                        self._events.append(
                            {
                                "type": "note_off",
                                "delta": delta_time,
                                "absolute": absolute_time,
                                "track": track_num,
                                "channel": channel,
                                "note": note,
                                "velocity": velocity,
                            }
                        )
                        if debug:
                            print(
                                f"Note Off: note={note}, velocity={velocity}, time={absolute_time}"
                            )
                    elif event_type == 0x90:
                        if offset + 1 >= len(data):
                            raise MIDIParseError(f"Incomplete Note On event at offset {offset}")
                        note = data[offset]
                        velocity = data[offset + 1]
                        offset += 2
                        if velocity == 0:
                            self._events.append(
                                {
                                    "type": "note_off",
                                    "delta": delta_time,
                                    "absolute": absolute_time,
                                    "track": track_num,
                                    "channel": channel,
                                    "note": note,
                                    "velocity": 0,
                                }
                            )
                            if debug:
                                print(
                                    "Note Off (via note-on velocity=0):"
                                    + f"note={note}, time={absolute_time}"
                                )
                        else:
                            self._events.append(
                                {
                                    "type": "note_on",
                                    "delta": delta_time,
                                    "absolute": absolute_time,
                                    "track": track_num,
                                    "channel": channel,
                                    "note": note,
                                    "velocity": velocity,
                                }
                            )
                            if debug:
                                print(
                                    f"Note On: note={note},"
                                    + f"velocity={velocity}, time={absolute_time}"
                                )
                    elif event_type == 0xB0:
                        if offset + 1 >= len(data):
                            raise MIDIParseError(f"Incomplete Controller event at offset {offset}")
                        controller = data[offset]
                        value = data[offset + 1]
                        offset += 2
                        self._events.append(
                            {
                                "type": "controller",
                                "delta": delta_time,
                                "absolute": absolute_time,
                                "track": track_num,
                                "channel": channel,
                                "controller": controller,
                                "value": value,
                            }
                        )
                    elif event_type == 0xC0:
                        if offset >= len(data):
                            raise MIDIParseError(
                                f"Incomplete Program Change event at offset {offset}"
                            )
                        program = data[offset]
                        offset += 1
                        self._events.append(
                            {
                                "type": "program_change",
                                "delta": delta_time,
                                "absolute": absolute_time,
                                "track": track_num,
                                "channel": channel,
                                "program": program,
                            }
                        )
                    elif event_type == 0xE0:
                        if offset + 1 >= len(data):
                            raise MIDIParseError(f"Incomplete Pitch Bend event at offset {offset}")
                        lsb = data[offset]
                        msb = data[offset + 1]
                        offset += 2
                        value = (msb << 7) | lsb
                        self._events.append(
                            {
                                "type": "pitch_bend",
                                "delta": delta_time,
                                "absolute": absolute_time,
                                "track": track_num,
                                "channel": channel,
                                "value": value,
                            }
                        )
                    elif status == 0xFF:
                        if offset >= len(data):
                            raise MIDIParseError(f"Incomplete Meta event at offset {offset}")
                        meta_type = data[offset]
                        offset += 1
                        if offset >= len(data):
                            raise MIDIParseError(f"Incomplete Meta event length at offset {offset}")
                        length, offset = self._read_variable_length(data, offset)
                        if offset + length > len(data):
                            raise MIDIParseError(
                                "Meta event extends beyond file end:"
                                + f"{offset + length} > {len(data)}"
                            )
                        if meta_type == 0x51 and length == 3:
                            self._tempo = (
                                (data[offset] << 16) | (data[offset + 1] << 8) | data[offset + 2]
                            )
                            self._events.append(
                                {
                                    "type": "tempo",
                                    "delta": delta_time,
                                    "absolute": absolute_time,
                                    "track": track_num,
                                    "tempo": self._tempo,
                                }
                            )
                            if debug:
                                print(f"Tempo: {self._tempo} microseconds per quarter note")
                        elif meta_type == 0x2F:
                            self._events.append(
                                {
                                    "type": "end_of_track",
                                    "delta": delta_time,
                                    "absolute": absolute_time,
                                    "track": track_num,
                                }
                            )
                            if debug:
                                print(f"End of Track {track_num}")
                        offset += length
                    elif status in {0xF0, 0xF7}:
                        if offset >= len(data):
                            raise MIDIParseError(f"Incomplete SysEx event at offset {offset}")
                        length, offset = self._read_variable_length(data, offset)
                        if offset + length > len(data):
                            raise MIDIParseError(
                                "SysEx event extends beyond file end:"
                                + f"{offset + length} > {len(data)}"
                            )
                        offset += length
                    else:
                        raise MIDIParseError(
                            f"Unknown event type: {hex(status)} at offset {offset-1}"
                        )
                offset = track_end
            self._events.sort(key=lambda x: x["absolute"])
            self._parsed = len(self._events) > 0
            if not self._parsed:
                raise MIDIParseError("No valid MIDI events found in file")
        except Exception as e:
            raise MIDIParseError(f"Error parsing MIDI file: {e}") from e

    def reset(self) -> None:
        """
        Reset playback to the beginning of the file.

        This resets the current event index and absolute time tracking.
        """
        self._current_event_index = 0
        self._last_absolute_time = 0

    def calculate_delay(self, event: Dict[str, Any]) -> float:
        """
        Calculate the delay in seconds until the next event.

        :param dict event: The current event
        :return: Delay in seconds until the next event
        :rtype: float
        """
        if self._current_event_index < len(self._events):
            next_event = self._events[self._current_event_index]
            time_diff = next_event["absolute"] - event["absolute"]
            if time_diff > 0:
                return (time_diff / self._ticks_per_beat) * (self._tempo / 1000000)
        return 0.1


class MIDIPlayer:
    """
    Class for playing MIDI files with timing control.
    Subclass this and override the event handler methods to customize behavior.

    :param MIDIParser midi_parser: A MIDIParser instance with a parsed MIDI file
    """

    def __init__(self, midi_parser: MIDIParser) -> None:
        """
        Initialize the MIDI player.

        :param MIDIParser midi_parser: A MIDIParser instance
        :raises MIDIParseError: If the provided parser hasn't parsed a file yet
        """
        if not midi_parser.parsed:
            raise MIDIParseError("MIDI parser must parse a file before creating a player")

        self._parser: MIDIParser = midi_parser
        self._playing: bool = False
        self._last_event_time: float = 0
        self._next_event_delay: float = 0
        self._loop_playback: bool = False
        self._finished: bool = False
        self._restart_delay: float = 3.0

    @property
    def restart_delay(self) -> float:
        """
        Delay in seconds before restarting playback when looping.
        Default is 3.0 seconds.
        """
        return self._restart_delay

    @restart_delay.setter
    def restart_delay(self, delay: float) -> None:
        """
        The delay in seconds before restarting playback when looping.

        :param float delay: Delay in seconds (minimum 0.1s)
        """
        self._restart_delay = max(0.1, float(delay))  # Minimum 0.1 second

    @property
    def playing(self) -> bool:
        """Whether the player is currently playing."""
        return self._playing

    @property
    def parser(self) -> MIDIParser:
        """The MIDIParser instance used by this player."""
        return self._parser

    @property
    def loop_playback(self) -> bool:
        """Whether playback should automatically loop when finished."""
        return self._loop_playback

    @loop_playback.setter
    def loop_playback(self, value: bool) -> None:
        """

        :param bool value: True to enable looping, False to disable
        """
        self._loop_playback = bool(value)

    @property
    def finished(self) -> bool:
        """Whether playback has completed (and not set to loop)."""
        return self._finished

    def stop(self) -> None:
        """
        Stop playback.

        This halts playback completely. Use reset() on the parser to
        return to the beginning of the file.
        """
        self._playing = False

    def pause(self) -> None:
        """
        Pause playback.

        Temporarily stops playback, which can be resumed from the current position.
        """
        self._playing = False

    def resume(self) -> None:
        """
        Resume playback from current position.

        If playback has finished, call reset() on the parser first to restart from the beginning.
        """
        if not self._playing and not self._finished:
            self._playing = True
            self._last_event_time = time.monotonic()

    def on_note_on(self, note: int, velocity: int, channel: int) -> None:
        """
        Called when a note-on event is processed.

        Override this method in a subclass to handle note-on events.

        :param int note: MIDI note number (0-127)
        :param int velocity: Note velocity (0-127)
        :param int channel: MIDI channel (0-15)
        """
        pass

    def on_note_off(self, note: int, velocity: int, channel: int) -> None:
        """
        Called when a note-off event is processed.

        Override this method in a subclass to handle note-off events.

        :param int note: MIDI note number (0-127)
        :param int velocity: Note velocity (0-127)
        :param int channel: MIDI channel (0-15)
        """
        pass

    def on_tempo_change(self, tempo: int) -> None:
        """
        Called when a tempo change event is processed.

        Override this method in a subclass to handle tempo changes.

        :param int tempo: New tempo in microseconds per quarter note
        """
        pass

    def on_end_of_track(self, track: int) -> None:
        """
        Called when an end-of-track event is processed.

        Override this method in a subclass to handle end-of-track events.

        :param int track: Track number, or -1 for end of all tracks
        """
        pass

    def on_playback_complete(self) -> None:
        """
        Called when playback reaches the end of the file.

        Override this method in a subclass to handle playback completion.
        If loop_playback is True, playback will restart automatically
        after this method returns.
        """
        pass

    def on_controller(self, controller: int, value: int, channel: int) -> None:
        """
        Called when a controller event is processed.

        Override this method in a subclass to handle controller events.

        :param int controller: Controller number
        :param int value: Controller value
        :param int channel: MIDI channel (0-15)
        """
        pass

    def on_program_change(self, program: int, channel: int) -> None:
        """
        Called when a program change event is processed.

        Override this method in a subclass to handle program change events.

        :param int program: Program number
        :param int channel: MIDI channel (0-15)
        """
        pass

    def play(self, loop: Optional[bool] = None) -> bool:  # noqa: PLR0912
        """
        Play the MIDI file. If already playing, process the next event.

        Call this method in your main loop to continuously play the MIDI file.

        :param Optional[bool] loop: Set to True to enable looping, False to disable, or None
        :return: True if an event was processed, False otherwise
        :rtype: bool
        """
        if loop is not None:
            self.loop_playback = bool(loop)
        if not self._playing:
            self._parser.reset()
            self._finished = False
            self._last_event_time = time.monotonic()
            self._next_event_delay = 0.05
            self._playing = True
        if not self._parser.parsed:
            raise MIDIParseError("Cannot play: MIDI parser must parse a file first")

        current_time = time.monotonic()
        if current_time - self._last_event_time >= self._next_event_delay:
            event = self._parser.current_event
            if event:
                current_absolute_time = event["absolute"]
                while (
                    self._parser.current_event
                    and self._parser.current_event["absolute"] == current_absolute_time
                ):
                    event = self._parser.next_event
                    if event["type"] == "note_on":
                        self.on_note_on(event["note"], event["velocity"], event["channel"])
                    elif event["type"] == "note_off":
                        self.on_note_off(event["note"], event["velocity"], event["channel"])
                    elif event["type"] == "tempo":
                        self.on_tempo_change(event["tempo"])
                    elif event["type"] == "controller":
                        self.on_controller(event["controller"], event["value"], event["channel"])
                    elif event["type"] == "program_change":
                        self.on_program_change(event["program"], event["channel"])
                    elif event["type"] == "end_of_track":
                        self.on_end_of_track(event["track"])
                if self._parser.current_event:
                    time_diff = self._parser.current_event["absolute"] - current_absolute_time
                    self._next_event_delay = (time_diff / self._parser.ticks_per_beat) * (
                        self._parser.tempo / 1000000
                    )
                else:
                    self._next_event_delay = 0.1
                self._last_event_time = current_time
            else:
                self._playing = False
                self._finished = True
                self.on_playback_complete()
                if self._loop_playback:
                    self._parser.reset()
                    self._playing = True
                    self._finished = False
                    self._last_event_time = current_time
                    self._next_event_delay = self._restart_delay
