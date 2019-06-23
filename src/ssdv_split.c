#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>
#include <unistd.h>

void ssdv_dec_call(uint32_t code, char *call)
{
	const char *ssdv_abc = "-0123456789---ABCDEFGHIJKLMNOPQRSTUVWXYZ";

	for (unsigned i = 0; i < 6 && code; i++) {
		call[i] = ssdv_abc[code % 40];
		code /= 40;
	}
}


int main(int argc, char **argv)
{
	uint8_t packet[256];
	FILE *fi = stdin, *fo = stdout;
	FILE *ssdv_out = NULL;
	char call_last[6] = {0};
	int iid_last = -1;


	if (chdir("rx_images") != 0) {
		perror("Failed changing to rx_images");
		return 1;
	}

	while (fread(&packet, sizeof(packet), 1, fi) == 1) {
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
		//bool eoi = packet[11] & 0x4;

		memcpy(&code, packet + 2, 4);
		code = ntohl(code);
		ssdv_dec_call(code, call);

		memcpy(&pid, packet + 7, 2);
		pid = ntohs(pid);

		if (iid != iid_last || strncmp(call, call_last, 6) != 0) {
			while (iid < iid_last)
				iid += 0x100;
			if (ssdv_out) {
				fclose(ssdv_out);
				ssdv_out = NULL;

				char path[32];
				snprintf(path, sizeof(path), "%.6s-%04d.ssdv",
					call_last, iid_last);
				if (rename("rx.tmp", path) != 0)
					perror("Error renaming rx.tmp");
			}
			iid_last = iid;
			strncpy(call_last, call, sizeof(call_last));

			ssdv_out = fopen("rx.tmp", "w+");
		}
		if (!ssdv_out) {
			perror("ssdv_out");
			continue;
		}

		fwrite(&packet, sizeof(packet), 1, ssdv_out);

		fprintf(stderr, "SSDV packet: %6s %3u %5u\n", call, iid, pid);
	}

	return 0;
}
