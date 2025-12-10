import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
    return (
        <Html lang="fr">
            <Head>
                <link
                    rel="stylesheet"
                    href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap"
                />
                <link rel="icon" href="/favicon.ico" />
            </Head>
            <body className="antialiased bg-slate-50 text-slate-900 font-body">
                <Main />
                <NextScript />
            </body>
        </Html>
    )
}
