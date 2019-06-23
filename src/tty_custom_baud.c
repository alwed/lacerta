/* Set custom terminal speed under Linux
 * https://stackoverflow.com/questions/12646324/how-to-set-a-custom-baud-rate-on-linux
 */

#include <stropts.h>
#include <asm/termios.h>

int tty_custom_speed(int fd, int speed)
{
	int ret;
	struct termios2 tio2;

	ret = ioctl(fd, TCGETS2, &tio2);
	if (ret != 0)
		return ret;

	tio2.c_cflag &= ~CBAUD;
	tio2.c_cflag |= BOTHER;
	tio2.c_ispeed = speed;
	tio2.c_ospeed = speed;

	ret = ioctl(fd, TCSETS2, &tio2);
	if (ret != 0)
		return ret;

	return 0;
}
