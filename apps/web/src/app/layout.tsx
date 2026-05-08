import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'EchoInsight',
  description: 'Audio & video transcription and summarization',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
