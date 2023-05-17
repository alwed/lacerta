#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <arpa/inet.h>
#include <errno.h>
#include <sys/stat.h>
#include <poll.h>
#include <unistd.h>

void ssdv_dec_call(uint32_t code, char *call)
{
	const char *ssdv_abc = "-0123456789---ABCDEFGHIJKLMNOPQRSTUVWXYZ";

	for (unsigned i = 0; i < 6 && code; i++) {
		call[i] = ssdv_abc[code % 40];
		code /= 40;
	}
}

void finalize_image(FILE **f, char *call, int iid, int pid)
{
	if (!*f)
		return;
	fprintf(stderr, "Finalizing image\n");

	fclose(*f);
	*f = NULL;

	char path[32];
	snprintf(path, sizeof(path), "%.6s-%04d-%05d.ssdv", call, iid, pid);
	if (rename("rx.tmp", path) != 0)
		perror("Error renaming rx.tmp");
}

int main(int argc, char **argv)
{
	uint8_t packet[256];
	FILE *fi = stdin, *fo = stdout;
	FILE *ssdv_out = NULL;
	char call_last[6] = {0};
	int iid_last = -1;
	int pid_last = -1;

	if (mkdir("rx_images", 0777) != 0 && errno != EEXIST) {
		perror("Failed creating directory rx_images");
		return 1;
	}

	if (chdir("rx_images") != 0) {
		perror("Failed changing to rx_images");
		return 1;
	}

	while (true) {
		struct pollfd pfd = {
			.fd = fileno(fi),
			.events = POLLIN,
			.revents = 0
		};
		int np = poll(&pfd, 1, 10000);
		if (np == 0) {
			//fprintf(stderr, "Timeout\n");
			finalize_image(&ssdv_out, call_last, iid_last, pid_last);
			continue;
		} else if (np < 0 || pfd.revents & (POLLERR | POLLNVAL)) {
			perror("poll");
			break;
		}

		size_t nr = fread(&packet, sizeof(packet), 1, fi);
		if (nr != 1)
			break;

		switch (packet[0]) {
		case 0x55:
			break;
		case 0x79:
		case 0x80:
			fwrite(&packet, sizeof(packet), 1, fo);
			fflush(fo);
		default:
			continue;
		}

		uint32_t code;
		uint16_t pid;
		char call[6];
		int iid = packet[6];
		bool eoi = packet[11] & 0x4;

		memcpy(&code, packet + 2, 4);
		code = ntohl(code);
		ssdv_dec_call(code, call);

		memcpy(&pid, packet + 7, 2);
		pid = ntohs(pid);

		bool newcall = strncmp(call, call_last, 6);
		if (newcall)
			iid_last = -1;

		while (iid < iid_last)
			iid += 0x100;
		bool newiid = iid != iid_last;

		if (newiid || newcall)
			finalize_image(&ssdv_out, call_last, iid_last, pid_last);

		pid_last = pid;
		iid_last = iid;
		strncpy(call_last, call, sizeof(call_last));

		if (!ssdv_out)
			ssdv_out = fopen("rx.tmp", "w");
		if (!ssdv_out) {
			perror("open ssdv_out");
			continue;
		}

		size_t nw = fwrite(&packet, sizeof(packet), 1, ssdv_out);
		if (nw < 1)
			perror("write ssdv");

		fprintf(stderr, "SSDV packet: %6s %3u %5u %s\n", call, iid, pid,
				eoi ? "EOI" : "");

		if (eoi)
			finalize_image(&ssdv_out, call, iid, pid);
	}
	fprintf(stderr, "End of input\n");
	finalize_image(&ssdv_out, call_last, iid_last, pid_last);

	return 0;
}
