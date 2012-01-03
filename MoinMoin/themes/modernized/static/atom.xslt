<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:dc="http://purl.org/dc/elements/1.1/" >
    <xsl:output method="html" />
    <xsl:template match="/">
        <html>
            <head>
                <title><xsl:value-of select="/atom:feed/atom:title" /></title>
            </head>
            <body>
                <xsl:apply-templates select="atom:feed" />
                <script type="text/javascript"><![CDATA[
                    var entries = document.getElementsByTagName('div');

                    var elements = [];
                    for (i = 0; i < entries.length; i++)
                    {
                        if (entries[i].className != 'summary')
                            continue;
                            
                        elements[elements.length] = entries[i];
                    }
                    
                    for (i = 0; i < elements.length; i++)
                        elements[i].innerHTML = elements[i].innerText;
                ]]></script>
            </body>
        </html>
    </xsl:template>
    <xsl:template match="atom:feed">
        <div style="color: red;">This is just a fallback version, please use a proper atom feed reader</div>
        <div style="font-size: 2.4em; text-align: center;"><xsl:value-of select="atom:title" /></div>
        <div id="entries">
            <xsl:apply-templates select="atom:entry" />
        </div>
    </xsl:template>
    <xsl:template match="atom:feed/atom:entry">
        <div style="margin: 2em; border-top: solid 1px #ddd; padding: 1em 0;">
            <div style="font-size: 1.4em;"><xsl:value-of select="atom:title" /></div>
            <div style="font-size: 0.9em; color: #999;"><xsl:value-of select="atom:author/atom:name" />, <xsl:value-of select="atom:updated" /></div>
            <div style="padding: 0px 30px 0px 30px;" class="summary"><xsl:value-of select="atom:summary" /></div>
        </div>
    </xsl:template>
</xsl:stylesheet>