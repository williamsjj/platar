# DigiTar Sophos AV IDE Updater #

The updater runs at a specified interval, downloads the latest IDE (IDentity Engine) files from Sophos, and pings the SAVDI daemon to reload it's databases. It parses the SAVDI configuration file to determine where to unpack the new IDE files, what ownership they should have, and where the PID file for SAVDI is located.


## Requirements ##

* Python 2.6 and [argparse 1.2.1](pypi.python.org/pypi/argparse/1.2.1)

__OR__

* Python 2.7

## License ##

Distributed under the BSD license.

	Redistribution and use in source and binary forms, with or without modification, 
	   are permitted provided that the following conditions are met:
	
	       * Redistributions of source code must retain the above copyright notice, 
	         this list of conditions and the following disclaimer.
	       * Redistributions in binary form must reproduce the above copyright notice, 
	         this list of conditions and the following disclaimer in the documentation 
	         and/or other materials provided with the distribution.
	       * Neither the name of DigiTar nor the names of its contributors may be
	         used to endorse or promote products derived from this software without 
	         specific prior written permission.
	
	THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY 
	EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES 
	OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT 
	SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, 
	INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED 
	TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR 
	BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
	CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN 
	ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH 
	DAMAGE.