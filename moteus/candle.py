# Copyright 2025 mjbots Robotic Systems, LLC.  info@mjbots.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .candle_device import CandleDevice
from .transport_wrapper import TransportWrapper


class Candle(TransportWrapper):
    """Convenience transport wrapping a single CandleDevice channel.

    Usage::

        transport = moteus.Candle()           # first available channel
        transport = moteus.Candle(channel_index=1)
        transport = moteus.Candle(serial_number='ABCD1234', channel_index=0)
    """

    def __init__(self, *args, **kwargs):
        device = CandleDevice(*args, **kwargs)
        super().__init__(device)
