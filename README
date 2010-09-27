# Kajiki: Really fast well-formed xml templates

Are you tired of the slow performance of Genshi? But
you still long for the assurance that your output is well-formed that you
miss from all those other templating engines? Do you wish you had Jinja's
blocks with Genshi's syntax? Then look  no further, Kajiki is for you!
Kajiki quickly compiles Genshi-like syntax to *real python bytecode*
that renders with blazing-fast speed! Don't delay! Pick up your
copy of Kajiki today!

## QuickStart

    >>> import kajiki
    >>> Template = kajiki.XMLTemplate('''<html>
    ...     <head><title>$title</title></head>
    ...     <body>
    ...         <h1>$title</h1>
    ...         <ul>
    ...             <li py:for="x in range(repetitions)">$title</li>
    ...         </ul>    
    ...     </body>
    ... </html>''')
    >>> print Template(dict(title='Kajiki is teh awesome!', repetitions=3)).render()
    <html>
        <head><title>Kajiki is teh awesome!</title></head>
        <body>
            <h1>Kajiki is teh awesome!</h1>
            <ul>
                <li>Kajiki is teh awesome!</li><li>Kajiki is teh awesome!</li><li>Kajiki is teh awesome!</li>
            </ul>    
        </body>
    </html>
