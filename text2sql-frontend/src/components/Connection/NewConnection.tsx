import { api } from "../../api";
import { Spinner } from "../Spinner/Spinner";
import { enqueueSnackbar } from "notistack";
import { isAxiosError } from "axios";

import { useState } from "react";
import { Radio, RadioField, RadioGroup } from "@catalyst/radio";
import { Description, Label } from "@catalyst/fieldset";
import { SampleSelector } from "./SampleSelector";
import ConnectionCreator from "./ConnectionCreator";


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

  type RadioValue = "sample" | "custom" | null;
  const [selectedRadio, setSelectedRadio] = useState<RadioValue>(null);
  const handleRadioChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    if (value !== "sample" && value !== "custom") {
      return;
    }
    setSelectedRadio(value);
  };

  const clearInputs = () => {
    setUnmaskedDsn("");
    setConnectionName("");
  };


  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setConnectionName(value);
  };

  // const createTestConnection = async () => {
  //   try {
  //     const res = await api.createTestConnection();
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
      await api.createConnection(unmaskedDsn, connectionName, false);
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
    <div className="dark:bg-gray-900 w-full h-full relative flex flex-col mt-16 lg:mt-0">
      <div className="flex flex-col lg:mt-0 p-4 lg:p-24">

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

          <div className="mt-12 sm:col-span-4">
            <label
              htmlFor="dsn"
              className="block text-sm font-medium leading-6 text-white mb-4"
            >
              Data Source Type
            </label>

            <RadioGroup name="resale" defaultValue="" onChange={(event) => setSelectedRadio(event as RadioValue)}>
              <RadioField>
                <Radio value="sample" />
                <Label>Choose a sample dataset</Label>
                <Description>Samples allow you to get started quickly</Description>
              </RadioField>
              <RadioField>
                <Radio value="custom" />
                <Label>Setup a custom connection</Label>
                <Description>Connect to your local databases or files</Description>
              </RadioField>
            </RadioGroup>
          </div>
        </div>

        {(selectedRadio === "sample") && <SampleSelector />}
        {selectedRadio === "custom" && <ConnectionCreator />}

      </div>
    </div>
  );

};
