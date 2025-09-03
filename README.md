# KBase
This job was part of the research on figuring out the relationships between bacteriophages and plasmids using current samples and comparing the genetic sequences to find conserved regions. This was run in parts using different tools provided by KBase

Workflow of my data processing using Kbase analytical tools for phage-plasmid research

- Metadata was collected from the alloted SRP accesion files
- Each entry was introduced to Fastqc
- After the job was run, it was connected to Trimmomatic and then Megahit and checked for the presence of contigs (a continuous stretch of DNA formed by the computational assembly of shorter, overlapping DNA fragments)

1. FastQC
Purpose: Quality control check.
It evaluates the raw sequence reads (FASTQ files) and generates reports on sequence quality, GC content, presence of adapters, overrepresented sequences, and base composition. It helps you decide whether your raw sequencing data is good enough for downstream analysis or if trimming/cleaning is required.

2. Trimmomatic
Purpose: Read trimming and cleaning.
It removes low-quality bases, trims adapters, and discards very short or poor-quality reads. Prepares high-quality reads by cleaning up the raw data before assembly or mapping. This step is often guided by the FastQC report.

3. MEGAHIT
Purpose: De novo metagenome assembly.
It assembles short reads (usually Illumina) into longer contiguous sequences (contigs).
After trimming, MEGAHIT takes the cleaned reads and assembles them into contigs, which can then be used for gene prediction, functional annotation, or binning genomes.

Finally we get an entire genome of the bacteriophage or plasmid in consideration and that is compared using supercomputers.
