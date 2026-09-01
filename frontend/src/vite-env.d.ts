/** @type {import('react').FunctionComponent} */
declare namespace React {
  interface FunctionComponent<P = {}> {
    (props: P): React.ReactElement | null
  }
}
