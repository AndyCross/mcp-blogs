# {{ .Title }}
{{ with .Description }}
> {{ . }}
{{ end }}
> Published: {{ .Date.Format "2006-01-02" }}

{{ .RawContent }}
