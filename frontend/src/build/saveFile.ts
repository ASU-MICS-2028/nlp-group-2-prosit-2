// Makes the browser save a file the page already holds in memory (a Blob).
// There is no "save" function in the browser, so the usual way is a hidden link with a `download` name that we click.
export function saveFile(file: Blob, name: string): void {
  const address = URL.createObjectURL(file) // a temporary address that points at the Blob
  const link = document.createElement('a')
  link.href = address
  link.download = name // `download` tells the browser to save it instead of opening it
  document.body.appendChild(link)
  link.click()
  link.remove()
  // Free the memory. A moment later, because some browsers read the address after the click returns.
  setTimeout(() => URL.revokeObjectURL(address), 1000)
}
