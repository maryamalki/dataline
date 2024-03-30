import { api } from "../../api";
import { Spinner } from "../Spinner/Spinner";
import { enqueueSnackbar } from "notistack";
import { isAxiosError } from "axios";

import {useState} from "react";

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(" ");
}

export const NewConnection = () => {

  // Flow in this component:
  // A. Enter name of connection
  // B. Select radio deciding if SAMPLE or CUSTOM connection
  // C. If SAMPLE, show SampleSelector component
  // D. If CUSTOM, show ConnectionCreator component

  const [unmaskedDsn, setUnmaskedDsn] = useState("");
  const [connectionName, setConnectionName] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const clearInputs = () => {
    setUnmaskedDsn("");
    setConnectionName("");
  };

  const handleDSNChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setUnmaskedDsn(value);
  };

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setConnectionName(value);
  };

  // const createTestConnection = async () => {
  //   try {
  //     const res = await api.createTestConnection();
  //     if (res.status !== "ok") {
  //       enqueueSnackbar({
  //         variant: "error",
  //         message: "Error creating connection",
  //       });
  //       setIsLoading(false);
  //       return;
  //     }
  //   } catch (exception) {
  //     if (isAxiosError(exception) && exception.response?.status === 409) {
  //       // Connection already exists, skip creation but don't close or clear modal
  //       enqueueSnackbar({
  //         variant: "info",
  //         message: "Connection already exists, skipping creation",
  //       });
  //       setIsLoading(false);
  //       return;
  //     } else {
  //       enqueueSnackbar({
  //         variant: "error",
  //         message: "Error creating connection",
  //       });
  //       setIsLoading(false);
  //       return;
  //     }
  //   }
  // }


  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    // Enable loading state
    setIsLoading(true);
    try {
      const res = await api.createConnection(unmaskedDsn, connectionName);
      if (res.status !== "ok") {
        enqueueSnackbar({
          variant: "error",
          message: "Error creating connection",
        });
        setIsLoading(false);
        return;
      }
    } catch (exception) {
      if (isAxiosError(exception) && exception.response?.status === 409) {
        // Connection already exists, skip creation but don't close or clear modal
        enqueueSnackbar({
          variant: "info",
          message: "Connection already exists, skipping creation",
        });
        setIsLoading(false);
        return;
      } else {
        enqueueSnackbar({
          variant: "error",
          message: "Error creating connection",
        });
        setIsLoading(false);
        return;
      }
    }

    setIsLoading(false);
    clearInputs();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-12">
      <div className="">
        <h2 className="text-base font-semibold leading-7 text-white">
          New Connection
        </h2>
        <p className="mt-1 text-sm leading-6 text-gray-400">
          Add a new database connection
        </p>

        <div className="mt-5 grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-6">
          <div className="sm:col-span-3">
            <label
              htmlFor="name"
              className="block text-sm font-medium leading-6 text-white"
            >
              Name
            </label>
            <div className="mt-2">
              <input
                type="text"
                name="name"
                id="name"
                disabled={isLoading}
                autoComplete="one-time-code"
                value={connectionName}
                onChange={handleNameChange}
                placeholder="Postgres Prod"
                className={classNames(
                  isLoading
                    ? "animate-pulse bg-gray-900 text-gray-400"
                    : "bg-white/5 text-white",
                  "block w-full rounded-md border-0 py-1.5 shadow-sm ring-1 ring-inset ring-white/10 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm sm:leading-6"
                )}
              />
            </div>
          </div>
        </div>

        <div className="mt-5 sm:col-span-4">
          <label
            htmlFor="dsn"
            className="block text-sm font-medium leading-6 text-white"
          >
            Connection string / DSN
          </label>

          {/* Display the masked DSN to the user */}
          <div className="relative mt-2">
            <input
              id="dsn"
              name="dsn"
              type="text"
              disabled={isLoading}
              autoComplete="one-time-code"
              value={unmaskedDsn}
              onChange={handleDSNChange}
              placeholder="postgres://myuser:mypassword@localhost:5432/mydatabase"
              // readOnly // Make this input read-only to prevent user interaction
              className={classNames(
                isLoading
                  ? "animate-pulse bg-gray-900 text-gray-400"
                  : "bg-white/5 text-white",
                "block w-full rounded-md border-0 py-1.5 font-mono shadow-sm ring-1 ring-inset ring-white/10 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm sm:leading-6"
              )}
            />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-end gap-x-6">
        <button
          disabled={!connectionName || !unmaskedDsn}
          type="submit"
          className={classNames(
            "inline-flex items-center rounded-md bg-indigo-500 px-4 py-2 text-sm font-semibold text-white shadow-sm",
            "hover:bg-indigo-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500",
            "disabled:bg-gray-600 disabled:hover:bg-gray-600 disabled:text-gray-300"
          )}
        >
          {isLoading && (
            // <Spinner className="pointer-events-none h-5 w-5"></Spinner>
            <Spinner />
          )}
          Save
        </button>
      </div>
    </form>
  );

};
